from __future__ import annotations

from dataclasses import dataclass, field
from html import unescape
from typing import Callable, Protocol
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from .sourcing import ProductCandidate


@dataclass(frozen=True)
class SearchProviderResult:
    success: bool
    provider: str
    candidates: list[ProductCandidate] = field(default_factory=list)
    error_message: str | None = None
    errors: list[dict[str, str]] = field(default_factory=list)
    normalized_intent: dict = field(default_factory=dict)
    common_filters: list[str] = field(default_factory=list)
    product_attributes: list[dict] = field(default_factory=list)
    sourcing_guidance: dict = field(default_factory=dict)


class SearchProvider(Protocol):
    name: str

    def search(self, query_text: str, max_results: int) -> SearchProviderResult:
        ...


class SearchProviderRouter:
    def __init__(self, providers: list[SearchProvider]) -> None:
        self.providers = providers

    def search(self, query_text: str, max_results: int) -> SearchProviderResult:
        errors: list[dict[str, str]] = []
        for provider in self.providers:
            result = provider.search(query_text, max_results)
            if result.success and result.candidates:
                return SearchProviderResult(
                    success=True,
                    provider=result.provider,
                    candidates=result.candidates,
                    errors=errors + result.errors,
                    normalized_intent=result.normalized_intent,
                    common_filters=result.common_filters,
                    product_attributes=result.product_attributes,
                    sourcing_guidance=result.sourcing_guidance,
                )
            errors.append({"provider": result.provider, "error": result.error_message or "no usable candidates"})
        return SearchProviderResult(success=False, provider="router", error_message="no provider returned usable candidates", errors=errors)


class MadeInChinaPublicProvider:
    name = "made_in_china_public"

    def __init__(
        self,
        base_url: str = "https://www.made-in-china.com/products-search/hot-china-products",
        fetch_html: Callable[[str], str] | None = None,
    ) -> None:
        self.base_url = base_url
        self.fetch_html = fetch_html or self._fetch_html

    def search(self, query_text: str, max_results: int) -> SearchProviderResult:
        separator = "&" if "?" in self.base_url else "?"
        url = f"{self.base_url}{separator}word={quote(query_text)}"
        return self.search_url(url, max_results=max_results)

    def search_url(self, url: str, max_results: int) -> SearchProviderResult:
        if not _is_allowed_public_url(url):
            return SearchProviderResult(
                success=False,
                provider=self.name,
                error_message="Made-in-China provider uses public pages only",
            )
        try:
            html = self.fetch_html(url)
        except Exception as exc:
            return SearchProviderResult(success=False, provider=self.name, error_message=str(exc))
        candidates = _extract_public_candidates(html, url, max_results)
        context = extract_public_filter_context(html)
        return SearchProviderResult(
            success=bool(candidates) or bool(context["commonFilters"] or context["productAttributes"]),
            provider=self.name,
            candidates=candidates,
            common_filters=context["commonFilters"],
            product_attributes=context["productAttributes"],
            sourcing_guidance=context["sourcingGuidance"],
            normalized_intent=context["normalizedIntent"],
        )

    @staticmethod
    def _fetch_html(url: str) -> str:
        request = Request(url, headers={"User-Agent": "product-sourcing-mvp/0.1 clean-room public-page fetch"})
        with urlopen(request, timeout=20) as response:
            return response.read().decode("utf-8", errors="replace")


class GenericWebSearchProvider:
    name = "generic_web"

    def __init__(self, search_connector) -> None:
        self.search_connector = search_connector

    def search(self, query_text: str, max_results: int) -> SearchProviderResult:
        try:
            results = self.search_connector.search(query_text)
        except Exception as exc:
            return SearchProviderResult(success=False, provider=self.name, error_message=str(exc))
        candidates = [
            ProductCandidate(
                title=result.title,
                product_url=result.url,
                description=result.snippet,
                source_url=result.url,
                source_domain=urlparse(result.url).netloc,
                extraction_method=f"search_result:{result.engine}",
                confidence=min(1.0, max(0.0, float(result.score or 0.0) / 100.0)),
            )
            for result in results[:max_results]
        ]
        return SearchProviderResult(success=bool(candidates), provider=self.name, candidates=candidates)


def _is_allowed_public_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    lowered = url.lower()
    forbidden = ("api/", "/api", "login", "signin", "captcha", "token", "private", "ajax")
    return not any(marker in lowered for marker in forbidden)


def _extract_public_candidates(html: str, source_url: str, max_results: int) -> list[ProductCandidate]:
    import re

    candidates: list[ProductCandidate] = []
    source_domain = urlparse(source_url).netloc
    # Clean-room lightweight extraction: gather visible-ish links that look product-related.
    for match in re.finditer(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", html, flags=re.I | re.S):
        href, label = match.groups()
        title = re.sub(r"<[^>]+>", " ", label)
        title = re.sub(r"\s+", " ", title).strip()
        if not title or len(title) < 4:
            continue
        absolute = href if href.startswith("http") else f"https://{source_domain}/{href.lstrip('/')}"
        if not _is_allowed_public_url(absolute):
            continue
        evidence_text = f"{title} {label}".lower()
        supplier_badges = []
        if "manufacturer" in evidence_text or "factory" in evidence_text:
            supplier_badges.append("Manufacturer")
        if "audited" in evidence_text:
            supplier_badges.append("Audited Supplier")
        if "verified" in evidence_text:
            supplier_badges.append("Verified Supplier")
        candidates.append(
            ProductCandidate(
                title=title,
                product_url=absolute,
                supplier_name=source_domain,
                supplier_badges=supplier_badges,
                is_verified_supplier="verified" in evidence_text,
                is_audited_supplier="audited" in evidence_text,
                supports_customization="customization" in evidence_text or "customized" in evidence_text,
                sample_available="sample available" in evidence_text,
                attributes={"sourcePlatform": "made-in-china"},
                source_url=source_url,
                source_domain=urlparse(absolute).netloc,
                extraction_method="made_in_china_public_html",
                confidence=0.45,
                field_evidence={"title": title, "url": absolute},
            )
        )
        if len(candidates) >= max_results:
            break
    return candidates


def extract_public_filter_context(html: str) -> dict:
    panel = _panel_html(html)
    text = _compact_text(_strip_tags(panel))
    common_filters: list[str] = []
    product_attributes: list[dict] = []
    normalized_intent: dict = {}
    guidance: dict = {}

    originals = _section_tags(panel, "Originals:")
    if originals:
        normalized_intent["originals"] = originals
        common_filters.extend(originals)

    commonly_used = _section_tags(panel, "Commonly Used:")
    if _contains_price_filter(panel):
        common_filters.append("Price range")
    common_filters.extend(commonly_used)

    summary = _class_text(panel, "groupSummary")
    if summary:
        guidance["qualityIndicators"] = [summary]

    for row_html in _row_blocks(panel):
        title = _row_title(row_html)
        values = _row_values(row_html)
        if title and values:
            product_attributes.append({"name": title.rstrip(":"), "values": values, **({"summary": summary} if summary else {})})

    return {
        "normalizedIntent": normalized_intent,
        "commonFilters": _dedupe(common_filters),
        "productAttributes": product_attributes,
        "sourcingGuidance": guidance,
    }


def _panel_html(html: str) -> str:
    import re

    match = re.search(r"<div[^>]+id=[\"']j-unified-attr-panel[\"'][^>]*>(.*)</div>", html or "", flags=re.I | re.S)
    return match.group(0) if match else (html or "")


def _section_tags(html: str, title: str) -> list[str]:
    import re

    marker = re.escape(title)
    match = re.search(marker + r"(.*?)(?:TopFilterRows-module_sectionTitle|OthersAttrSections-module_wrap|index-module_footer|$)", html, flags=re.I | re.S)
    if not match:
        return []
    section = match.group(1)
    return [_compact_text(_strip_tags(item)) for item in re.findall(r"<div[^>]+module_tag[^>]*>(.*?)</div>", section, flags=re.I | re.S) if _compact_text(_strip_tags(item))]


def _contains_price_filter(html: str) -> bool:
    return "priceFilter" in html or "placeholder=\"Minimum\"" in html or "placeholder='Minimum'" in html


def _row_blocks(html: str) -> list[str]:
    import re

    return re.findall(r"<div[^>]+OthersAttrSections-module_row__[^>]*>(.*?)(?=<div[^>]+OthersAttrSections-module_row__|</div></div></div></div>|$)", html, flags=re.I | re.S)


def _row_title(row_html: str) -> str:
    import re

    match = re.search(r"<span[^>]+OthersAttrSections-module_field[^>]*>(.*?)</span>", row_html, flags=re.I | re.S)
    return _compact_text(_strip_tags(match.group(1))) if match else ""


def _row_values(row_html: str) -> list[str]:
    import re

    values = []
    for raw in re.findall(r"<div[^>]+OthersAttrSections-module_tag[^>]*>(.*?)</div>", row_html, flags=re.I | re.S):
        value = _compact_text(_strip_tags(raw))
        if value:
            values.append(value)
    return _dedupe(values)


def _class_text(html: str, class_marker: str) -> str:
    import re

    match = re.search(rf"<div[^>]+{re.escape(class_marker)}[^>]*>(.*?)</div>", html, flags=re.I | re.S)
    return _compact_text(_strip_tags(match.group(1))) if match else ""


def _strip_tags(value: str) -> str:
    import re

    return re.sub(r"<[^>]+>", " ", unescape(value or " "))


def _compact_text(value: str) -> str:
    import re

    return re.sub(r"\s+", " ", unescape(value or "")).strip()


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        normalized = _compact_text(value)
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result
