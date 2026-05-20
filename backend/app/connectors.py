from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from email.message import EmailMessage
from email.utils import format_datetime, getaddresses, make_msgid, parsedate_to_datetime
from html.parser import HTMLParser
import imaplib
import ipaddress
import json
import os
import re
import shlex
import smtplib
import ssl
import subprocess
from typing import Any, Callable, Protocol
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse
from urllib.request import Request, urlopen

from .agent import ConnectorResult, ModelProvider, ToolRegistry
from .config import Settings
from .model_providers import parse_model_json


INITIALIZE_PARAMS = {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {"name": "product-sourcing-mvp", "version": "0.1.0"},
}

READ_LINKS_CODE = """
() => {
  return Array.from(document.querySelectorAll('a[href]'))
    .map((link) => ({
      title: (link.textContent || '').trim(),
      url: new URL(link.getAttribute('href'), document.baseURI).href
    }));
}
""".strip()

EXTRACT_PRODUCT_CODE = """
() => {
    const text = (selector) => {
      const node = document.querySelector(selector);
      return node && node.textContent ? node.textContent.trim() : null;
    };
    const attr = (selector, name) => {
      const node = document.querySelector(selector);
      return node ? node.getAttribute(name) : null;
    };
    const meta = (...names) => {
      for (const name of names) {
        const value = attr(`meta[property="${name}"], meta[name="${name}"]`, 'content');
        if (value) return value.trim();
      }
      return null;
    };
    const first = (...values) => {
      for (const value of values.flat()) {
        if (value !== undefined && value !== null && String(value).trim() !== '') {
          return String(value).trim();
        }
      }
      return null;
    };
    const pairs = {};
    for (const dt of Array.from(document.querySelectorAll('dt'))) {
      const dd = dt.nextElementSibling;
      if (dd && dd.tagName.toLowerCase() === 'dd') {
        pairs[(dt.textContent || '').trim().toLowerCase()] = (dd.textContent || '').trim();
      }
    }
    const attributes = {};
    if (pairs.attributes) {
      for (const item of pairs.attributes.split(';')) {
        const [key, ...rest] = item.split('=');
        if (key && rest.length) {
          attributes[key.trim()] = rest.join('=').trim();
        }
      }
    }
    const jsonLdItems = [];
    for (const script of Array.from(document.querySelectorAll('script[type="application/ld+json"]'))) {
      try {
        const parsed = JSON.parse(script.textContent || 'null');
        const queue = Array.isArray(parsed) ? [...parsed] : [parsed];
        while (queue.length) {
          const item = queue.shift();
          if (!item || typeof item !== 'object') continue;
          jsonLdItems.push(item);
          if (Array.isArray(item['@graph'])) queue.push(...item['@graph']);
        }
      } catch (_ignored) {}
    }
    const hasType = (item, type) => {
      const raw = item && item['@type'];
      const values = Array.isArray(raw) ? raw : [raw];
      return values.some((value) => String(value || '').toLowerCase() === type);
    };
    const productLd = jsonLdItems.find((item) => hasType(item, 'product')) || {};
    const organizationLd = jsonLdItems.find((item) => hasType(item, 'organization')) || {};
    const offers = Array.isArray(productLd.offers) ? productLd.offers[0] : (productLd.offers || {});
    const brand = typeof productLd.brand === 'object' ? productLd.brand.name : productLd.brand;
    const imageValue = productLd.image;
    const images = []
      .concat(Array.isArray(imageValue) ? imageValue : imageValue ? [imageValue] : [])
      .concat(meta('og:image', 'twitter:image') || [])
      .filter(Boolean)
      .map((value) => new URL(String(value), document.baseURI).href);
    const emailValues = new Set();
    const normalizeEmailCandidate = (value) => String(value || '')
      .replace(/\\s*(?:\\(|\\[|\\{)?\\s*at\\s*(?:\\)|\\]|\\})?\\s*/ig, '@')
      .replace(/\\s*(?:\\(|\\[|\\{)?\\s*dot\\s*(?:\\)|\\]|\\})?\\s*/ig, '.')
      .replace(/\\s+/g, '')
      .trim();
    const addEmailCandidate = (value) => {
      const normalized = normalizeEmailCandidate(value);
      if (/^[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}$/i.test(normalized)) {
        emailValues.add(normalized);
      }
    };
    const decodeCfEmail = (encoded) => {
      try {
        const key = parseInt(encoded.slice(0, 2), 16);
        let email = '';
        for (let index = 2; index < encoded.length; index += 2) {
          email += String.fromCharCode(parseInt(encoded.slice(index, index + 2), 16) ^ key);
        }
        return email;
      } catch (_ignored) {
        return '';
      }
    };
    for (const link of Array.from(document.querySelectorAll('a[href^="mailto:"]'))) {
      addEmailCandidate(link.getAttribute('href').replace(/^mailto:/i, '').split('?')[0].trim());
    }
    const bodyText = document.body ? document.body.innerText : '';
    for (const match of bodyText.matchAll(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}/gi)) {
      addEmailCandidate(match[0]);
    }
    const fullText = [bodyText, document.documentElement ? document.documentElement.textContent : ''].join('\\n');
    for (const match of fullText.matchAll(/[A-Z0-9._%+-]+\\s*(?:\\(|\\[|\\{)?\\s*at\\s*(?:\\)|\\]|\\})?\\s*[A-Z0-9.-]+\\s*(?:\\(|\\[|\\{)?\\s*dot\\s*(?:\\)|\\]|\\})?\\s*[A-Z]{2,}/gi)) {
      addEmailCandidate(match[0]);
    }
    for (const node of Array.from(document.querySelectorAll('[data-cfemail]'))) {
      addEmailCandidate(decodeCfEmail(node.getAttribute('data-cfemail') || ''));
    }
    const telegramValues = new Set();
    for (const link of Array.from(document.querySelectorAll('a[href*="t.me/"], a[href*="telegram.me/"]'))) {
      telegramValues.add(link.href);
    }
    for (const match of bodyText.matchAll(/(?:^|\\s)(@[A-Za-z0-9_]{5,})/g)) {
      telegramValues.add(match[1]);
    }
    const contacts = [];
    for (const email of emailValues) contacts.push({ type: 'email', value: email });
    for (const telegram of telegramValues) contacts.push({ type: 'telegram', value: telegram });
    const contactType = pairs['contact type'] || null;
    const contactValue = pairs.contact || null;
    if (contactType && contactValue) contacts.unshift({ type: contactType, value: contactValue });
    const contactLinkTerms = /(contact|contacts|contact-us|sales|support|customer-service|dealer|dealers|distributor|distributors|where-to-buy|about|impressum)/i;
    const contactLinks = [];
    const seenContactLinks = new Set();
    for (const link of Array.from(document.querySelectorAll('a[href]'))) {
      const label = [
        link.textContent || '',
        link.getAttribute('href') || '',
        link.getAttribute('aria-label') || '',
        link.getAttribute('title') || ''
      ].join(' ');
      if (!contactLinkTerms.test(label)) continue;
      const href = new URL(link.getAttribute('href'), document.baseURI).href.split('#')[0];
      if (!seenContactLinks.has(href)) {
        seenContactLinks.add(href);
        contactLinks.push(href);
      }
      if (contactLinks.length >= 12) break;
    }
    const image = document.querySelector('article img, img');
    const priceText = first(
      offers.price,
      attr('[itemprop="price"]', 'content'),
      text('[itemprop="price"]'),
      text('[class*="price" i], [data-price], [id*="price" i]'),
      pairs.price
    );
    const normalizePrice = (value) => {
      if (!value) return null;
      const match = String(value).replace(/\\s+/g, ' ').match(/[-+]?\\d[\\d\\s,.]*/);
      if (!match) return null;
      const raw = match[0].replace(/\\s/g, '');
      if (raw.includes(',') && !raw.includes('.')) return raw.replace(',', '.');
      return raw.replace(/,/g, '');
    };
    const currencyText = first(
      offers.priceCurrency,
      attr('[itemprop="priceCurrency"]', 'content'),
      text('[itemprop="priceCurrency"]'),
      pairs.currency,
      priceText && String(priceText).match(/\\b(USD|EUR|GBP|RUB|CNY|JPY)\\b/i)?.[1],
      priceText && String(priceText).includes('$') ? 'USD' : null,
      priceText && String(priceText).includes('\u20ac') ? 'EUR' : null,
      priceText && String(priceText).includes('\u00a3') ? 'GBP' : null
    );
    return {
      title: first(productLd.name, text('article h1, h1, [data-product-title]'), meta('og:title', 'twitter:title'), document.title),
      productUrl: window.location.href,
      price: normalizePrice(priceText),
      currency: currencyText || null,
      supplierName: first(pairs.supplier, organizationLd.name, brand, meta('og:site_name'), location.hostname),
      contacts,
      images: images.length ? images : (image && image.src ? [image.src] : []),
      description: first(productLd.description, text('article .description, [data-description]'), meta('description', 'og:description', 'twitter:description')),
      attributes: Object.assign({}, attributes, {
        sku: first(productLd.sku, pairs.sku),
        brand: first(brand, pairs.brand),
        availability: first(offers.availability, pairs.availability),
        contactLinks: contactLinks.length ? JSON.stringify(contactLinks) : null
      })
    };
}
""".strip()


class McpClient(Protocol):
    def initialize(self) -> None:
        ...

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        ...

    def close(self) -> None:
        ...


class McpProtocolError(RuntimeError):
    pass


class BrowserSecurityError(ValueError):
    pass


@dataclass(frozen=True)
class WebSearchResult:
    title: str
    url: str
    snippet: str = ""
    engine: str = ""
    score: float = 0.0


@dataclass(frozen=True)
class InboundEmailMessage:
    external_id: str
    subject: str
    body: str
    from_address: str
    to_address: str
    in_reply_to: str = ""
    references: str = ""
    provider_timestamp: datetime | None = None


class WebSearchConnector(Protocol):
    def search(self, query: str) -> list[WebSearchResult]:
        ...


class McpStdioClient:
    def __init__(
        self,
        command: list[str],
        timeout_seconds: int = 30,
        process_factory: Callable[..., Any] = subprocess.Popen,
    ) -> None:
        if not command:
            raise ValueError("MCP stdio command is required")
        self.command = command
        self.timeout_seconds = timeout_seconds
        self.process_factory = process_factory
        self._process: Any | None = None
        self._next_id = 1
        self._initialized = False

    def initialize(self) -> None:
        self._ensure_process()
        self._request("initialize", INITIALIZE_PARAMS)
        self._notify("notifications/initialized")
        self._initialized = True

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self._initialized:
            self.initialize()
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        if not isinstance(result, dict):
            raise McpProtocolError(f"MCP tool {name} returned non-object result")
        return result

    def close(self) -> None:
        if self._process is None:
            return
        try:
            self._process.terminate()
        except Exception:
            pass
        self._process = None
        self._initialized = False

    def _ensure_process(self) -> None:
        if self._process is not None:
            return
        self._process = self.process_factory(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

    def _request(self, method: str, params: dict[str, Any]) -> Any:
        request_id = self._next_id
        self._next_id += 1
        self._write({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        while True:
            message = self._read()
            if message.get("id") != request_id:
                continue
            if message.get("error"):
                raise McpProtocolError(_jsonrpc_error_text(message["error"]))
            return message.get("result")

    def _notify(self, method: str) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": {}})

    def _write(self, message: dict[str, Any]) -> None:
        if self._process is None or self._process.stdin is None:
            raise McpProtocolError("MCP process is not running")
        self._process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self._process.stdin.flush()

    def _read(self) -> dict[str, Any]:
        if self._process is None or self._process.stdout is None:
            raise McpProtocolError("MCP process is not running")
        line = self._process.stdout.readline()
        if not line:
            raise McpProtocolError("MCP process closed stdout")
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            raise McpProtocolError(f"MCP returned invalid JSON: {line[:200]}") from exc
        if not isinstance(message, dict):
            raise McpProtocolError("MCP returned non-object JSON-RPC message")
        return message


class McpHttpClient:
    def __init__(
        self,
        endpoint_url: str,
        timeout_seconds: int = 30,
        http_post: Callable[[str, dict[str, Any], dict[str, str], int], tuple[int, dict[str, str], str]] | None = None,
    ) -> None:
        if not endpoint_url:
            raise ValueError("MCP HTTP endpoint URL is required")
        self.endpoint_url = endpoint_url
        self.timeout_seconds = timeout_seconds
        self.http_post = http_post or self._urllib_post
        self._next_id = 1
        self._session_id: str | None = None
        self._initialized = False

    def initialize(self) -> None:
        self._request("initialize", INITIALIZE_PARAMS)
        self._notify("notifications/initialized")
        self._initialized = True

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self._initialized:
            self.initialize()
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        if not isinstance(result, dict):
            raise McpProtocolError(f"MCP tool {name} returned non-object result")
        return result

    def close(self) -> None:
        self._initialized = False

    def _request(self, method: str, params: dict[str, Any]) -> Any:
        request_id = self._next_id
        self._next_id += 1
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        status, headers, body = self.http_post(self.endpoint_url, payload, self._headers(), self.timeout_seconds)
        self._capture_session(headers)
        if status >= 400:
            raise McpProtocolError(f"MCP HTTP returned status {status}")
        message = _parse_http_mcp_body(body, expected_id=request_id)
        if message.get("id") != request_id:
            raise McpProtocolError("MCP HTTP returned response for a different request")
        if message.get("error"):
            raise McpProtocolError(_jsonrpc_error_text(message["error"]))
        return message.get("result")

    def _notify(self, method: str) -> None:
        payload = {"jsonrpc": "2.0", "method": method, "params": {}}
        status, headers, _body = self.http_post(self.endpoint_url, payload, self._headers(), self.timeout_seconds)
        self._capture_session(headers)
        if status >= 400:
            raise McpProtocolError(f"MCP HTTP notification returned status {status}")

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        return headers

    def _capture_session(self, headers: dict[str, str]) -> None:
        for key, value in headers.items():
            if key.lower() == "mcp-session-id":
                self._session_id = value

    @staticmethod
    def _urllib_post(
        endpoint_url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout_seconds: int,
    ) -> tuple[int, dict[str, str], str]:
        request = Request(
            endpoint_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
            return response.status, dict(response.headers.items()), body


@dataclass
class SearxngWebSearchConnector:
    search_url: str
    result_limit: int = 20
    timeout_seconds: int = 30
    http_get: Callable[[str, int], tuple[int, str]] | None = None

    def search(self, query: str) -> list[WebSearchResult]:
        endpoint = self._search_endpoint(query)
        status, body = (self.http_get or self._urllib_get)(endpoint, self.timeout_seconds)
        if status >= 400:
            raise RuntimeError(f"SearXNG returned HTTP {status}")
        data = json.loads(body or "{}")
        results = []
        seen_urls: set[str] = set()
        for item in data.get("results") or []:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            url = _normalize_search_result_url(str(item.get("url") or "").strip())
            if not title or not url or url in seen_urls:
                continue
            seen_urls.add(url)
            results.append(
                WebSearchResult(
                    title=title,
                    url=url,
                    snippet=str(item.get("content") or item.get("snippet") or "").strip(),
                    engine=str(item.get("engine") or "").strip(),
                    score=float(item.get("score") or 0.0),
                )
            )
            if len(results) >= self.result_limit:
                break
        return results

    def _search_endpoint(self, query: str) -> str:
        separator = "&" if "?" in self.search_url else "?"
        params = urlencode(
            {
                "q": query,
                "format": "json",
                "categories": "general",
                "language": "all",
                "safesearch": "0",
            }
        )
        return f"{self.search_url}{separator}{params}"

    @staticmethod
    def _urllib_get(endpoint_url: str, timeout_seconds: int) -> tuple[int, str]:
        request = Request(endpoint_url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=timeout_seconds) as response:
            return response.status, response.read().decode("utf-8")


@dataclass
class DuckDuckGoHtmlWebSearchConnector:
    search_url: str = "https://duckduckgo.com/html/"
    result_limit: int = 20
    timeout_seconds: int = 30
    http_get: Callable[[str, int], tuple[int, str]] | None = None

    def search(self, query: str) -> list[WebSearchResult]:
        endpoint = self._search_endpoint(query)
        status, body = (self.http_get or self._urllib_get)(endpoint, self.timeout_seconds)
        if status >= 400:
            raise RuntimeError(f"DuckDuckGo returned HTTP {status}")
        parser = _DuckDuckGoHtmlParser()
        parser.feed(body or "")
        results = []
        seen_urls: set[str] = set()
        for item in parser.results:
            title = item["title"].strip()
            url = _without_fragment(_normalize_search_result_url(item["url"].strip()))
            if not title or not url or url in seen_urls:
                continue
            if urlparse(url).scheme not in {"http", "https"}:
                continue
            seen_urls.add(url)
            results.append(WebSearchResult(title=title, url=url, snippet=item.get("snippet", ""), engine="duckduckgo"))
            if len(results) >= self.result_limit:
                break
        return results

    def _search_endpoint(self, query: str) -> str:
        separator = "&" if "?" in self.search_url else "?"
        return f"{self.search_url}{separator}{urlencode({'q': query})}"

    @staticmethod
    def _urllib_get(endpoint_url: str, timeout_seconds: int) -> tuple[int, str]:
        request = Request(
            endpoint_url,
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "User-Agent": "Mozilla/5.0 product-sourcing-mvp/0.1",
            },
        )
        with urlopen(request, timeout=timeout_seconds) as response:
            return response.status, response.read().decode("utf-8", errors="replace")


@dataclass
class MultiEngineWebSearchConnector:
    engines: list[WebSearchConnector]

    def __post_init__(self) -> None:
        if not self.engines:
            raise ValueError("WEB_SEARCH_ENGINES must include at least one engine")

    def search(self, query: str) -> list[WebSearchResult]:
        results: list[WebSearchResult] = []
        seen_urls: set[str] = set()
        errors: list[str] = []
        for engine in self.engines:
            try:
                engine_results = engine.search(query)
            except Exception as exc:
                errors.append(str(exc))
                continue
            for result in engine_results:
                normalized_url = _without_fragment(_normalize_search_result_url(result.url))
                if not normalized_url or normalized_url in seen_urls:
                    continue
                if urlparse(normalized_url).scheme not in {"http", "https"}:
                    continue
                seen_urls.add(normalized_url)
                results.append(
                    WebSearchResult(
                        title=result.title,
                        url=normalized_url,
                        snippet=result.snippet,
                        engine=result.engine,
                        score=result.score,
                    )
                )
        if not results and errors:
            raise RuntimeError(f"all web search engines failed: {'; '.join(errors)}")
        return results


class _DuckDuckGoHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self._current_link: dict[str, Any] | None = None
        self._current_snippet: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value or "" for key, value in attrs}
        classes = set(attributes.get("class", "").split())
        if tag == "a" and "result__a" in classes and attributes.get("href"):
            self._current_link = {"url": attributes["href"], "text": []}
        elif "result__snippet" in classes:
            self._current_snippet = []

    def handle_data(self, data: str) -> None:
        if self._current_link is not None:
            self._current_link["text"].append(data)
        if self._current_snippet is not None:
            self._current_snippet.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_link is not None:
            title = " ".join("".join(self._current_link["text"]).split())
            if title:
                self.results.append({"title": title, "url": self._current_link["url"], "snippet": ""})
            self._current_link = None
        if self._current_snippet is not None and tag in {"a", "div"}:
            snippet = " ".join("".join(self._current_snippet).split())
            if snippet and self.results and not self.results[-1].get("snippet"):
                self.results[-1]["snippet"] = snippet
            self._current_snippet = None


@dataclass
class PlaywrightMcpBrowserConnector:
    mcp_client_factory: Callable[[], McpClient]
    supplier_site_url: str
    allowed_domains: set[str]
    max_pages: int = 5
    research_mode: str = "site"
    allow_public_internet: bool = False
    search_url_template: str = "https://www.adafruit.com/search?q={query}"
    contact_enrichment_pages: int = 1

    def research(self, query_text: str, max_results: int | None = None) -> ConnectorResult:
        client = self.mcp_client_factory()
        try:
            mode, start_url = self._start(query_text)
            self.ensure_allowed_url(start_url)
            client.initialize()
            self._call_tool(client, "browser_navigate", {"url": start_url})
            link_result = self._call_tool(client, "browser_evaluate", {"function": READ_LINKS_CODE})
            candidate_links = self._candidate_links(parse_mcp_tool_json(link_result), query_text)
        except Exception as exc:
            return ConnectorResult(success=False, error_message=str(exc))
        finally:
            self._close_client(client)

        products: list[dict[str, Any]] = []
        candidate_errors: list[dict[str, str]] = []
        candidate_limit = _research_candidate_limit(self.max_pages, max_results)
        candidates_visited = 0
        for link in candidate_links[:candidate_limit]:
            if _has_enough_valid_products(products, max_results):
                break
            product_url = link["url"]
            candidates_visited += 1
            try:
                self.ensure_allowed_url(product_url)
                products.extend(self._extract_products_from_page(product_url))
            except Exception as exc:
                candidate_errors.append({"url": product_url, "error": str(exc)})
                products.append(_fallback_product_from_link(link))
        return ConnectorResult(
            success=True,
            payload={
                "products": products,
                "source": {
                    "provider": "playwright_mcp",
                    "mode": mode,
                    "startUrl": start_url,
                    "candidatesVisited": candidates_visited,
                    "candidateErrors": candidate_errors,
                },
            },
        )

    def extract_products_from_links(self, links: list[dict[str, str]], max_results: int | None = None) -> dict[str, Any]:
        products: list[dict[str, Any]] = []
        candidate_errors: list[dict[str, str]] = []
        candidate_limit = _research_candidate_limit(self.max_pages, max_results)
        candidates_visited = 0
        for link in links[:candidate_limit]:
            if _has_enough_valid_products(products, max_results):
                break
            product_url = link["url"]
            candidates_visited += 1
            try:
                self.ensure_allowed_url(product_url)
                extracted = self._extract_products_from_page(product_url)
                if not extracted:
                    products.append(_fallback_product_from_link(link))
                    continue
                for product in extracted:
                    self._enrich_product_contacts(product, link)
                    _annotate_product_with_discovery(product, link)
                    products.append(product)
            except Exception as exc:
                candidate_errors.append({"url": product_url, "error": str(exc)})
                products.append(_fallback_product_from_link(link))
        return {"products": products, "candidateErrors": candidate_errors, "candidatesVisited": candidates_visited}

    def ensure_allowed_url(self, url: str) -> None:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        netloc = parsed.netloc
        if parsed.scheme not in {"http", "https"} or not hostname:
            raise BrowserSecurityError(f"browser URL is not allowed: {url}")
        if self._is_explicitly_allowed(hostname, netloc):
            return
        if self.allow_public_internet and _is_public_internet_host(hostname):
            return
        raise BrowserSecurityError(f"browser URL is not in allowlist: {url}")

    def _start(self, query_text: str) -> tuple[str, str]:
        for match in re.findall(r"site:(https?://[^\s]+)", query_text):
            return "site", match.rstrip("/")
        if not self.supplier_site_url:
            raise BrowserSecurityError("TEST_SUPPLIER_SITE_URL is required for browser research")
        if self.research_mode.strip().lower() == "internet":
            query = re.sub(r"site:https?://[^\s]+", "", query_text, flags=re.IGNORECASE).strip()
            return "internet", self.search_url_template.format(query=quote(query))
        return "site", self.supplier_site_url.rstrip("/")

    def _is_explicitly_allowed(self, hostname: str, netloc: str) -> bool:
        normalized_hostname = hostname.lower()
        normalized_netloc = netloc.lower()
        allowed = {item.lower() for item in self.allowed_domains if item}
        for item in allowed:
            if item in {"*"}:
                continue
            if normalized_hostname == item or normalized_netloc == item:
                return True
            if normalized_hostname.endswith(f".{item}") and "." in item:
                return True
        return False

    def _candidate_links(self, payload: Any, query_text: str) -> list[dict[str, str]]:
        if isinstance(payload, list):
            raw_links = payload
        elif isinstance(payload, dict):
            raw_links = payload.get("links") or payload.get("products") or []
        else:
            raw_links = []

        query_terms = _meaningful_query_terms(query_text)
        candidates_by_url: dict[str, dict[str, str | int]] = {}
        for item in raw_links:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("text") or "").strip()
            url = _normalize_search_result_url(str(item.get("url") or item.get("href") or "").strip())
            if not title or not url:
                continue
            try:
                self.ensure_allowed_url(url)
            except BrowserSecurityError:
                continue
            if query_terms and not _title_matches(title, query_terms):
                continue
            normalized_url = _without_fragment(url)
            score = _score_candidate_link(title, normalized_url, query_terms)
            existing = candidates_by_url.get(normalized_url)
            if existing is None or score > int(existing["score"]):
                candidates_by_url[normalized_url] = {"title": title, "url": normalized_url, "score": score}
        ranked = sorted(
            candidates_by_url.values(),
            key=lambda candidate: (-int(candidate["score"]), str(candidate["title"]).lower(), str(candidate["url"])),
        )
        return [{"title": str(candidate["title"]), "url": str(candidate["url"])} for candidate in ranked]

    def _extract_products_from_page(self, product_url: str) -> list[dict[str, Any]]:
        client = self.mcp_client_factory()
        try:
            client.initialize()
            self._call_tool(client, "browser_navigate", {"url": product_url})
            product_result = self._call_tool(client, "browser_evaluate", {"function": EXTRACT_PRODUCT_CODE})
            products = []
            for product in _normalize_product_payloads(parse_mcp_tool_json(product_result)):
                product.setdefault("productUrl", product_url)
                products.append(product)
            return products
        finally:
            self._close_client(client)

    def _enrich_product_contacts(self, product: dict[str, Any], link: dict[str, str]) -> None:
        existing_contacts = product.get("contacts")
        if isinstance(existing_contacts, list) and existing_contacts:
            return
        product_url = str(product.get("productUrl") or link.get("url") or "").strip()
        enrichment_pages: list[str] = []
        contacts: list[dict[str, str]] = []
        if self.contact_enrichment_pages <= 0:
            return
        for page_url in _supplier_contact_candidate_pages(product_url, product)[: self.contact_enrichment_pages]:
            try:
                self.ensure_allowed_url(page_url)
                for payload in self._extract_products_from_page(page_url):
                    page_contacts = payload.get("contacts")
                    if isinstance(page_contacts, list):
                        contacts = _merge_contacts(contacts, page_contacts)
                if contacts:
                    enrichment_pages.append(page_url)
                    break
            except Exception:
                continue
        if contacts:
            product["contacts"] = _merge_contacts(product.get("contacts") if isinstance(product.get("contacts"), list) else [], contacts)
            attributes = product.setdefault("attributes", {})
            if isinstance(attributes, dict):
                attributes["enrichmentPages"] = ",".join(enrichment_pages)

    def _close_client(self, client: McpClient) -> None:
        try:
            self._call_tool(client, "browser_close", {})
        except Exception:
            pass
        client.close()

    @staticmethod
    def _call_tool(client: McpClient, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = client.call_tool(name, arguments)
        if result.get("isError"):
            raise McpProtocolError(_mcp_tool_error_text(result))
        return result


@dataclass
class AiInternetProductSearchConnector:
    model_provider: ModelProvider
    web_search: WebSearchConnector
    browser_connector: PlaywrightMcpBrowserConnector
    query_count: int = 3
    candidate_limit: int = 5

    def research(self, query_text: str, max_results: int | None = None) -> ConnectorResult:
        if _site_target(query_text):
            return self.browser_connector.research(query_text, max_results=max_results)
        try:
            candidate_limit = _research_candidate_limit(self.candidate_limit, max_results)
            queries = self._generate_queries(query_text)
            search_results = self._collect_search_results(queries)
            selected_links = self._select_candidates(query_text, search_results, candidate_limit)
            extraction = self.browser_connector.extract_products_from_links(
                selected_links[:candidate_limit],
                max_results=max_results,
            )
            return ConnectorResult(
                success=True,
                payload={
                    "products": extraction["products"],
                    "source": {
                        "provider": "ai_internet_product_search",
                        "mode": "ai_internet",
                        "model": self.model_provider.name,
                        "queries": queries,
                        "resultsCollected": len(search_results),
                        "candidatesVisited": extraction.get("candidatesVisited", len(selected_links[:candidate_limit])),
                        "candidateErrors": extraction["candidateErrors"],
                    },
                },
            )
        except Exception as exc:
            return ConnectorResult(success=False, error_message=str(exc))

    def _generate_queries(self, query_text: str) -> list[str]:
        prompt = (
            "Generate public web search queries for sourcing real product pages.\n"
            "Return JSON only in this schema: {\"queries\":[\"...\"]}.\n"
            "Use supplier/product search wording, include buy/supplier/distributor terms when useful.\n"
            f"User query: {query_text}"
        )
        try:
            payload = _model_json(self.model_provider, prompt)
        except Exception:
            payload = {}
        queries = [
            str(item).strip()
            for item in payload.get("queries", [])
            if str(item).strip()
        ]
        if not queries:
            queries = [query_text.strip()]
        queries.extend(_b2b_supplier_query_variants(query_text))
        return _unique_strings(queries)[: self.query_count]

    def _collect_search_results(self, queries: list[str]) -> list[WebSearchResult]:
        collected: list[WebSearchResult] = []
        seen_urls: set[str] = set()
        for query in queries:
            for result in self.web_search.search(query):
                normalized_url = _without_fragment(_normalize_search_result_url(result.url))
                if normalized_url in seen_urls:
                    continue
                try:
                    self.browser_connector.ensure_allowed_url(normalized_url)
                except BrowserSecurityError:
                    continue
                seen_urls.add(normalized_url)
                collected.append(
                    WebSearchResult(
                        title=result.title,
                        url=normalized_url,
                        snippet=result.snippet,
                        engine=result.engine,
                        score=result.score,
                    )
                )
        return collected

    def _select_candidates(
        self,
        query_text: str,
        results: list[WebSearchResult],
        candidate_limit: int | None = None,
    ) -> list[dict[str, str]]:
        if not results:
            return []
        limit = candidate_limit or self.candidate_limit
        prompt = (
            "Select likely product pages from web search results for a product sourcing task.\n"
            "Prefer direct product/detail pages from suppliers, distributors, marketplaces, or manufacturers.\n"
            "Reject categories, login pages, carts, blog posts, docs, unrelated pages, and unsafe URLs.\n"
            "Return JSON only in this schema: "
            "{\"selected\":[{\"title\":\"...\",\"url\":\"https://...\",\"reason\":\"...\"}]}.\n"
            f"User query: {query_text}\n"
            f"Search results:\n{_search_results_for_prompt(results)}"
        )
        try:
            payload = _model_json(self.model_provider, prompt)
        except Exception:
            payload = {}
        selected = []
        allowed_by_url = {result.url: result for result in results}
        for item in payload.get("selected", []):
            if not isinstance(item, dict):
                continue
            url = _without_fragment(_normalize_search_result_url(str(item.get("url") or "").strip()))
            if url not in allowed_by_url:
                continue
            try:
                self.browser_connector.ensure_allowed_url(url)
            except BrowserSecurityError:
                continue
            title = str(item.get("title") or allowed_by_url[url].title).strip()
            if title:
                selected.append(
                    _search_result_candidate_link(
                        allowed_by_url[url],
                        query_text,
                        reason=str(item.get("reason") or "").strip(),
                        title_override=title,
                    )
                )
        query_terms = _meaningful_query_terms(query_text)
        ranked = sorted(
            results,
            key=lambda result: (-_score_search_result_candidate(result, query_terms), result.title.lower(), result.url),
        )
        selected_urls = {item["url"] for item in selected}
        for result in ranked:
            if len(selected) >= limit:
                break
            if result.url in selected_urls:
                continue
            selected.append(_search_result_candidate_link(result, query_text))
            selected_urls.add(result.url)
        return selected[:limit]


@dataclass
class SmtpEmailConnector:
    host: str
    port: int
    from_address: str
    username: str = ""
    password: str = ""
    use_tls: bool = True
    use_ssl: bool = False
    timeout_seconds: int = 30
    smtp_factory: Callable[..., Any] | None = None

    def send(self, to: str, subject: str, body: str) -> ConnectorResult:
        try:
            self._validate()
            message = EmailMessage()
            message_id = make_msgid(domain=self.from_address.split("@")[-1])
            provider_timestamp = datetime.now(timezone.utc)
            message["Message-ID"] = message_id
            message["Date"] = format_datetime(provider_timestamp)
            message["From"] = self.from_address
            message["To"] = to
            message["Subject"] = subject
            message.set_content(body)

            smtp_factory = self.smtp_factory or (smtplib.SMTP_SSL if self.use_ssl else smtplib.SMTP)
            with smtp_factory(self.host, self.port, timeout=self.timeout_seconds) as smtp:
                if self.use_tls and not self.use_ssl:
                    smtp.starttls(context=ssl.create_default_context())
                if self.username:
                    smtp.login(self.username, self.password)
                smtp.send_message(message)
            return ConnectorResult(
                success=True,
                external_id=message_id,
                payload={"providerTimestamp": provider_timestamp.isoformat()},
            )
        except Exception as exc:
            return ConnectorResult(success=False, error_message=redact_secrets(str(exc), [self.password]))

    def _validate(self) -> None:
        if not self.host:
            raise ValueError("EMAIL_SMTP_HOST is required")
        if not self.port:
            raise ValueError("EMAIL_SMTP_PORT is required")
        if not self.from_address:
            raise ValueError("EMAIL_FROM is required")


@dataclass
class GmailImapInboundConnector:
    host: str
    port: int
    username: str
    password: str
    mailbox: str = "INBOX"
    timeout_seconds: int = 30
    imap_factory: Callable[..., Any] | None = None

    def fetch_unseen(self, limit: int = 20) -> ConnectorResult:
        client = None
        try:
            self._validate()
            factory = self.imap_factory or imaplib.IMAP4_SSL
            client = factory(self.host, self.port, timeout=self.timeout_seconds)
            client.login(self.username, self.password)
            client.select(self.mailbox)
            status, data = client.search(None, "ALL")
            if status != "OK":
                raise RuntimeError("Gmail IMAP search failed")
            ids = list(reversed((data[0] or b"").split()))[: max(1, int(limit))]
            messages = []
            for message_id in ids:
                status, fetched = client.fetch(message_id, "(RFC822)")
                if status != "OK":
                    continue
                raw = _imap_raw_message(fetched)
                if raw is None:
                    continue
                messages.append(_parse_inbound_email(raw))
            return ConnectorResult(success=True, payload={"messages": messages})
        except Exception as exc:
            return ConnectorResult(success=False, error_message=redact_secrets(str(exc), [self.password]))
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass
                try:
                    client.logout()
                except Exception:
                    pass

    def _validate(self) -> None:
        if not self.host:
            raise ValueError("EMAIL_IMAP_HOST is required")
        if not self.port:
            raise ValueError("EMAIL_IMAP_PORT is required")
        if not self.username:
            raise ValueError("EMAIL_IMAP_USER is required")
        if not self.password:
            raise ValueError("EMAIL_IMAP_PASSWORD is required")


@dataclass
class TelegramBotConnector:
    bot_token: str
    default_chat_id: str = ""
    timeout_seconds: int = 30
    http_post: Callable[[str, dict[str, Any], int], tuple[int, str]] | None = None

    def send(self, chat: str, body: str) -> ConnectorResult:
        try:
            self._validate()
            chat_id = chat.strip() or self.default_chat_id
            if not chat_id:
                raise ValueError("Telegram chat id is required")
            endpoint = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": body,
                "disable_web_page_preview": True,
            }
            status, response_body = (self.http_post or self._urllib_post)(
                endpoint,
                payload,
                self.timeout_seconds,
            )
            data = json.loads(response_body or "{}")
            if status >= 400 or not data.get("ok"):
                raise RuntimeError(data.get("description") or f"Telegram API returned HTTP {status}")
            message_id = data.get("result", {}).get("message_id")
            return ConnectorResult(success=True, external_id=str(message_id) if message_id is not None else None)
        except Exception as exc:
            return ConnectorResult(success=False, error_message=redact_secrets(str(exc), [self.bot_token]))

    def _validate(self) -> None:
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")

    @staticmethod
    def _urllib_post(endpoint_url: str, payload: dict[str, Any], timeout_seconds: int) -> tuple[int, str]:
        request = Request(
            endpoint_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=timeout_seconds) as response:
            return response.status, response.read().decode("utf-8")


def build_tool_registry(settings: Settings, model_provider: ModelProvider | None = None) -> ToolRegistry:
    registry = ToolRegistry()
    if settings.browser_provider:
        registry.register("browser_mcp", build_browser_connector(settings, model_provider))
    if settings.email_connector_provider:
        registry.register("email", build_email_connector(settings))
    if settings.email_inbound_provider:
        registry.register("gmail_inbound", build_gmail_inbound_connector(settings))
    if settings.telegram_connector_provider:
        registry.register("telegram", build_telegram_connector(settings))
    return registry


def build_browser_connector(
    settings: Settings,
    model_provider: ModelProvider | None = None,
) -> PlaywrightMcpBrowserConnector | AiInternetProductSearchConnector:
    provider = settings.browser_provider.strip().lower()
    if provider not in {"playwright_mcp", "playwright_local"}:
        raise ValueError(f"unsupported browser provider: {settings.browser_provider}")

    allowed_domains = _allowed_domains(settings)
    if settings.browser_mcp_url:
        client_factory = lambda: McpHttpClient(settings.browser_mcp_url)
    else:
        command = [settings.browser_mcp_command, *_split_args(settings.browser_mcp_args)]
        client_factory = lambda: McpStdioClient(command)

    browser_connector = PlaywrightMcpBrowserConnector(
        mcp_client_factory=client_factory,
        supplier_site_url=settings.test_supplier_site_url,
        allowed_domains=allowed_domains,
        max_pages=settings.internet_search_result_limit,
        research_mode=settings.browser_research_mode,
        allow_public_internet=settings.browser_allow_public_internet,
        search_url_template=settings.internet_search_url_template,
        contact_enrichment_pages=settings.search_contact_enrichment_pages,
    )
    if settings.browser_research_mode.strip().lower() != "ai_internet":
        return browser_connector
    if model_provider is None:
        raise ValueError("MODEL_PROVIDER is required for BROWSER_RESEARCH_MODE=ai_internet")
    return AiInternetProductSearchConnector(
        model_provider=model_provider,
        web_search=build_web_search_connector(settings),
        browser_connector=browser_connector,
        query_count=settings.ai_search_query_count,
        candidate_limit=settings.ai_search_candidate_limit,
    )


def build_web_search_connector(settings: Settings) -> WebSearchConnector:
    provider = settings.web_search_provider.strip().lower()
    if provider == "searxng":
        return SearxngWebSearchConnector(
            search_url=settings.web_search_url,
            result_limit=settings.web_search_result_limit,
        )
    if provider in {"duckduckgo", "duckduckgo_html"}:
        return DuckDuckGoHtmlWebSearchConnector(
            search_url=settings.web_search_url or "https://duckduckgo.com/html/",
            result_limit=settings.web_search_result_limit,
        )
    if provider == "multi":
        return MultiEngineWebSearchConnector(_parse_web_search_engines(settings))
    raise ValueError(f"unsupported web search provider: {settings.web_search_provider}")


def build_email_connector(settings: Settings) -> SmtpEmailConnector:
    provider = settings.email_connector_provider.strip().lower()
    if provider != "smtp":
        raise ValueError(f"unsupported email connector provider: {settings.email_connector_provider}")
    return SmtpEmailConnector(
        host=settings.email_smtp_host,
        port=settings.email_smtp_port,
        username=settings.email_smtp_user,
        password=settings.email_smtp_password,
        from_address=settings.email_from,
        use_tls=settings.email_use_tls,
        use_ssl=settings.email_use_ssl,
        timeout_seconds=settings.email_timeout_seconds,
    )


def build_gmail_inbound_connector(settings: Settings) -> GmailImapInboundConnector:
    provider = settings.email_inbound_provider.strip().lower()
    if provider not in {"gmail_imap", "imap"}:
        raise ValueError(f"unsupported email inbound provider: {settings.email_inbound_provider}")
    return GmailImapInboundConnector(
        host=settings.email_imap_host,
        port=settings.email_imap_port,
        username=settings.email_imap_user,
        password=settings.email_imap_password,
        mailbox=settings.email_imap_mailbox,
        timeout_seconds=settings.email_timeout_seconds,
    )


def build_telegram_connector(settings: Settings) -> TelegramBotConnector:
    provider = settings.telegram_connector_provider.strip().lower()
    if provider not in {"telegram_bot", "bot_api"}:
        raise ValueError(f"unsupported Telegram connector provider: {settings.telegram_connector_provider}")
    return TelegramBotConnector(
        bot_token=settings.telegram_bot_token,
        default_chat_id=settings.telegram_chat_id,
        timeout_seconds=settings.telegram_timeout_seconds,
    )


def parse_mcp_tool_json(result: dict[str, Any]) -> Any:
    if "structuredContent" in result:
        return result["structuredContent"]
    if "result" in result:
        return result["result"]
    if "content" not in result:
        return result

    texts = [
        str(item.get("text", ""))
        for item in result.get("content") or []
        if isinstance(item, dict) and item.get("type") == "text"
    ]
    text = "\n".join(part for part in texts if part).strip()
    if not text:
        return {}
    return json.loads(_extract_json_text(text))


def redact_secrets(message: str, secrets: list[str]) -> str:
    redacted = message
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "***REDACTED***")
    return redacted


def _imap_raw_message(fetched: Any) -> bytes | None:
    for item in fetched or []:
        if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], bytes):
            return item[1]
    return None


def _parse_inbound_email(raw: bytes) -> InboundEmailMessage:
    message = BytesParser(policy=policy.default).parsebytes(raw)
    body = _email_text_body(message)
    from_address = _first_email_address(message.get("From", ""))
    to_address = _first_email_address(message.get("To", ""))
    external_id = str(message.get("Message-ID") or message.get("X-GM-MSGID") or "").strip()
    if not external_id:
        external_id = f"imap:{hash(raw)}"
    return InboundEmailMessage(
        external_id=external_id,
        subject=str(message.get("Subject") or "").strip(),
        body=_clean_reply_body(body),
        from_address=from_address,
        to_address=to_address,
        in_reply_to=str(message.get("In-Reply-To") or "").strip(),
        references=str(message.get("References") or "").strip(),
        provider_timestamp=_parse_email_date(message.get("Date")),
    )


def _parse_email_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = parsedate_to_datetime(str(raw))
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _clean_reply_body(body: str) -> str:
    text = (body or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(">"):
            break
        if _is_quote_header(stripped):
            break
        lines.append(line)
    cleaned = "\n".join(lines).strip()
    cleaned = re.split(
        r"\s(?:on .+ wrote:|[а-яё]{2},\s+\d{1,2}\s+[а-яё]+\s+\d{4}.+?<[^>]+>:)",
        cleaned,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip()
    cleaned = re.split(r"\n\s*-{2,}\s*original message\s*-{2,}", cleaned, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    return cleaned or text


def _is_quote_header(line: str) -> bool:
    if not line:
        return False
    lower = line.lower()
    if lower.startswith("on ") and lower.endswith("wrote:"):
        return True
    if re.match(r"^[а-яё]{2,},?\s+\d{1,2}\s+[а-яё]+\s+\d{4}.+<[^>]+>:\s*$", line, flags=re.IGNORECASE):
        return True
    return "original message" in lower or "пересылаемое сообщение" in lower


def _email_text_body(message: Any) -> str:
    if message.is_multipart():
        plain_parts = []
        html_fallback = []
        for part in message.walk():
            if part.get_content_maintype() == "multipart":
                continue
            disposition = str(part.get_content_disposition() or "")
            if disposition == "attachment":
                continue
            content_type = part.get_content_type()
            try:
                content = part.get_content()
            except Exception:
                payload = part.get_payload(decode=True) or b""
                content = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
            if content_type == "text/plain":
                plain_parts.append(str(content))
            elif content_type == "text/html":
                html_fallback.append(re.sub(r"<[^>]+>", " ", str(content)))
        return "\n".join(plain_parts or html_fallback)
    try:
        return str(message.get_content())
    except Exception:
        payload = message.get_payload(decode=True) or b""
        return payload.decode(message.get_content_charset() or "utf-8", errors="replace")


def _first_email_address(raw: str) -> str:
    addresses = getaddresses([raw])
    return (addresses[0][1] if addresses else raw).strip().lower()


def _allowed_domains(settings: Settings) -> set[str]:
    domains = {item.strip().lower() for item in settings.browser_allowed_domains.split(",") if item.strip()}
    supplier = urlparse(settings.test_supplier_site_url)
    if supplier.hostname:
        domains.add(supplier.hostname.lower())
    if supplier.netloc:
        domains.add(supplier.netloc.lower())
    return domains


def _parse_web_search_engines(settings: Settings) -> list[WebSearchConnector]:
    engines = []
    for spec in settings.web_search_engines.split(","):
        raw = spec.strip()
        if not raw:
            continue
        name, separator, url = raw.partition(":")
        if not separator or not name.strip() or not url.strip():
            raise ValueError("WEB_SEARCH_ENGINES entries must use name:url format")
        engines.append(_build_web_search_engine(name.strip().lower(), url.strip(), settings))
    return engines


def _build_web_search_engine(name: str, search_url: str, settings: Settings) -> WebSearchConnector:
    if name == "searxng":
        return SearxngWebSearchConnector(
            search_url=search_url,
            result_limit=settings.web_search_result_limit,
        )
    if name in {"duckduckgo", "duckduckgo_html"}:
        return DuckDuckGoHtmlWebSearchConnector(
            search_url=search_url,
            result_limit=settings.web_search_result_limit,
        )
    raise ValueError(f"unsupported web search engine in WEB_SEARCH_ENGINES: {name}")


def _research_candidate_limit(default_limit: int, max_results: int | None) -> int:
    try:
        requested = int(max_results) if max_results is not None else default_limit
    except (TypeError, ValueError):
        requested = default_limit
    return max(1, min(max(default_limit, requested), 50))


def _normalize_search_result_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    for key in ("uddg", "u", "url"):
        values = query.get(key)
        if values:
            return unquote(values[0])
    return url


def _without_fragment(url: str) -> str:
    parsed = urlparse(url)
    return parsed._replace(fragment="").geturl()


def _is_public_internet_host(hostname: str) -> bool:
    host = hostname.strip().lower().rstrip(".")
    if not host:
        return False
    if host in {"localhost"} or host.endswith((".local", ".internal", ".localhost")):
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return "." in host
    return ip.is_global


def _split_args(raw: str) -> list[str]:
    if not raw.strip():
        return []
    return [_strip_surrounding_quotes(arg) for arg in shlex.split(raw, posix=os.name != "nt")]


def _strip_surrounding_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _parse_http_mcp_body(body: str, expected_id: int | None = None) -> dict[str, Any]:
    text = body.strip()
    if not text:
        return {}
    if text.startswith("event:") or text.startswith("data:"):
        messages = []
        event_lines: list[str] = []
        for line in text.splitlines():
            if line.startswith("data:"):
                event_lines.append(line.removeprefix("data:").strip())
            elif not line.strip() and event_lines:
                messages.append(_parse_mcp_json_message("\n".join(event_lines)))
                event_lines = []
        if event_lines:
            messages.append(_parse_mcp_json_message("\n".join(event_lines)))
        if not messages:
            raise McpProtocolError("MCP SSE response did not contain data")
        if expected_id is not None:
            for message in messages:
                if message.get("id") == expected_id:
                    return message
            raise McpProtocolError("MCP SSE response did not contain response for request")
        return messages[-1]
    return _parse_mcp_json_message(text)


def _parse_mcp_json_message(text: str) -> dict[str, Any]:
    message = json.loads(text)
    if not isinstance(message, dict):
        raise McpProtocolError("MCP HTTP returned non-object JSON")
    return message


def _jsonrpc_error_text(error: Any) -> str:
    if isinstance(error, dict):
        return str(error.get("message") or error)
    return str(error)


def _mcp_tool_error_text(result: dict[str, Any]) -> str:
    texts = [
        str(item.get("text", ""))
        for item in result.get("content") or []
        if isinstance(item, dict) and item.get("type") == "text"
    ]
    text = "\n".join(part for part in texts if part).strip()
    return text.removeprefix("### Error").strip() or "MCP tool returned an error"


def _strip_json_fence(text: str) -> str:
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
    return match.group(1) if match else text


def _extract_json_text(text: str) -> str:
    stripped = _strip_json_fence(text.strip())
    if not stripped.startswith("### Result"):
        return stripped
    result_block = stripped.removeprefix("### Result").strip()
    return result_block.split("\n###", 1)[0].strip()


def _normalize_product_payloads(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("products"), list):
        return [item for item in payload["products"] if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _site_target(query_text: str) -> str | None:
    match = re.search(r"site:(https?://[^\s]+)", query_text, flags=re.IGNORECASE)
    return match.group(1).rstrip("/") if match else None


def _model_json(model_provider: ModelProvider, prompt: str) -> dict[str, Any]:
    complete_json = getattr(model_provider, "complete_json", None)
    if callable(complete_json):
        payload = complete_json(prompt)
    else:
        payload = parse_model_json(model_provider.complete(prompt))
    if not isinstance(payload, dict):
        raise ValueError("model returned non-object JSON")
    return payload


def _unique_strings(values: list[str]) -> list[str]:
    seen = set()
    unique = []
    for value in values:
        normalized = value.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(value)
    return unique


def _search_results_for_prompt(results: list[WebSearchResult]) -> str:
    lines = []
    for index, result in enumerate(results[:40], start=1):
        lines.append(
            json.dumps(
                {
                    "index": index,
                    "title": result.title,
                    "url": result.url,
                    "snippet": result.snippet[:300],
                    "engine": result.engine,
                },
                ensure_ascii=False,
            )
        )
    return "\n".join(lines)


def _fallback_product_from_link(link: dict[str, str]) -> dict[str, Any]:
    product_url = link["url"]
    hostname = urlparse(product_url).hostname or urlparse(product_url).netloc
    price = _price_from_text(link["title"])
    payload: dict[str, Any] = {
        "title": link["title"],
        "productUrl": product_url,
        "supplierName": hostname,
        "contacts": [],
        "images": [],
        "attributes": {"extractionFallback": "search_result_link"},
    }
    _annotate_product_with_discovery(payload, link)
    if price is not None:
        payload["price"] = price
    currency = _currency_from_text(link["title"])
    if currency:
        payload["currency"] = currency
    return payload


def _base_search_query(query_text: str) -> str:
    query_without_site = re.sub(r"site:https?://[^\s]+", "", query_text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", query_without_site).strip()


def _b2b_supplier_query_variants(query_text: str) -> list[str]:
    base = _base_search_query(query_text)
    if not base:
        return []
    return [
        f"{base} supplier",
        f"{base} manufacturer",
        f"{base} distributor",
        f"{base} wholesale",
        f"{base} moq",
        f"{base} stock",
        f"{base} contact",
        f"{base} rfq",
        f"{base} price list",
        f"{base} authorized distributor",
    ]


def _search_result_candidate_link(
    result: WebSearchResult,
    query_text: str,
    *,
    reason: str = "",
    title_override: str = "",
) -> dict[str, str]:
    title = title_override or result.title
    supplier_type = _supplier_candidate_type(title, result.url, result.snippet)
    source_confidence = _source_confidence(supplier_type, title, result.url, result.snippet)
    candidate_reason = reason or _candidate_reason(supplier_type, title, result.url, result.snippet)
    return {
        "title": title,
        "url": result.url,
        "supplierType": supplier_type,
        "sourceConfidence": str(source_confidence),
        "candidateReason": candidate_reason,
        "candidateUrl": result.url,
        "discoveryQuery": _base_search_query(query_text),
        "searchEngine": result.engine,
    }


def _annotate_product_with_discovery(product: dict[str, Any], link: dict[str, str]) -> None:
    attributes = product.setdefault("attributes", {})
    if not isinstance(attributes, dict):
        attributes = {}
        product["attributes"] = attributes
    supplier_type = link.get("supplierType") or _supplier_candidate_type(
        str(product.get("title") or link.get("title") or ""),
        str(product.get("productUrl") or link.get("url") or ""),
    )
    attributes.setdefault("supplierType", supplier_type)
    attributes.setdefault(
        "sourceConfidence",
        link.get("sourceConfidence")
        or str(_source_confidence(supplier_type, str(product.get("title") or link.get("title") or ""), str(product.get("productUrl") or link.get("url") or ""))),
    )
    attributes.setdefault("candidateReason", link.get("candidateReason") or _candidate_reason(supplier_type, str(link.get("title") or ""), str(link.get("url") or "")))
    attributes.setdefault("candidateUrl", link.get("candidateUrl") or link.get("url") or str(product.get("productUrl") or ""))
    if link.get("discoveryQuery"):
        attributes.setdefault("discoveryQuery", link["discoveryQuery"])
    if link.get("searchEngine"):
        attributes.setdefault("searchEngine", link["searchEngine"])
    attributes["contactConfidence"] = str(_contact_confidence(product.get("contacts")))


def _supplier_candidate_type(title: str, url: str, snippet: str = "") -> str:
    text = f"{title} {url} {snippet}".lower()
    if any(marker in text for marker in ("login", "sign in", "signin", "/cart", "/basket", "/account")):
        return "blocked_or_account"
    if any(marker in text for marker in ("blog", "review", "article", "news", "forum", "youtube", "pinterest", "/docs/", "/documentation/")):
        return "content_page"
    if any(marker in text for marker in ("manufacturer", "factory", "oem", "odm", "producer", "made in")):
        return "manufacturer"
    if any(marker in text for marker in ("distributor", "authorized distributor", "reseller", "stock", "in stock", "inventory")):
        return "distributor"
    marketplaces = ("alibaba", "amazon.", "ebay.", "aliexpress", "digikey", "mouser", "arrow.com", "rs-online", "tme.eu")
    if any(marker in text for marker in marketplaces):
        return "marketplace"
    if any(marker in url.lower() for marker in ("/product/", "/products/", "/item/", "/items/", "/p/", "/dp/", "/sku/")):
        return "product_page"
    if any(marker in url.lower() for marker in ("/contact", "/about", "/sales", "/distributors")):
        return "contact_page"
    return "unknown"


def _source_confidence(supplier_type: str, title: str, url: str, snippet: str = "") -> int:
    confidence_by_type = {
        "manufacturer": 88,
        "distributor": 84,
        "marketplace": 72,
        "product_page": 68,
        "contact_page": 56,
        "unknown": 45,
        "content_page": 20,
        "blocked_or_account": 10,
    }
    score = confidence_by_type.get(supplier_type, 45)
    combined = f"{title} {url} {snippet}".lower()
    if any(marker in combined for marker in ("price", "moq", "wholesale", "rfq", "quote", "stock", "datasheet")):
        score += 5
    if any(marker in url.lower() for marker in ("/login", "/signin", "/cart", "/search")):
        score -= 20
    return max(0, min(100, score))


def _candidate_reason(supplier_type: str, title: str, url: str, snippet: str = "") -> str:
    if supplier_type == "manufacturer":
        return "manufacturer wording found"
    if supplier_type == "distributor":
        return "distributor or stock wording found"
    if supplier_type == "marketplace":
        return "known marketplace or catalog domain"
    if supplier_type == "product_page":
        return "direct product URL pattern"
    if supplier_type == "contact_page":
        return "supplier contact page"
    if supplier_type in {"content_page", "blocked_or_account"}:
        return "low-value sourcing page"
    return "search result candidate"


def _score_search_result_candidate(result: WebSearchResult, query_terms: list[str]) -> int:
    score = _score_candidate_link(result.title, result.url, query_terms)
    supplier_type = _supplier_candidate_type(result.title, result.url, result.snippet)
    score += {
        "manufacturer": 18,
        "distributor": 18,
        "marketplace": 10,
        "product_page": 9,
        "contact_page": 2,
        "unknown": 0,
        "content_page": -20,
        "blocked_or_account": -30,
    }.get(supplier_type, 0)
    score += result.score
    return score


def _supplier_contact_candidate_pages(product_url: str, product: dict[str, Any] | None = None) -> list[str]:
    candidates: list[str] = []
    if product:
        attributes = product.get("attributes")
        if isinstance(attributes, dict):
            candidates.extend(_attribute_contact_links(attributes.get("contactLinks")))
    candidates.extend(_supplier_domain_contact_pages(product_url))
    return _unique_strings([candidate for candidate in candidates if candidate])


def _attribute_contact_links(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not isinstance(value, str) or not value.strip():
        return []
    stripped = value.strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    return [item.strip() for item in stripped.split(",") if item.strip()]


def _supplier_domain_contact_pages(product_url: str) -> list[str]:
    parsed = urlparse(product_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return []
    base = f"{parsed.scheme}://{parsed.netloc}"
    return [
        f"{base}/contact",
        f"{base}/contact-us",
        f"{base}/contacts",
        f"{base}/support",
        f"{base}/customer-service",
        f"{base}/sales",
        f"{base}/where-to-buy",
        f"{base}/dealers",
        f"{base}/dealer-locator",
        f"{base}/distributor",
        f"{base}/distributors",
        f"{base}/about",
        f"{base}/about-us",
        f"{base}/impressum",
    ]


def _merge_contacts(existing: Any, discovered: Any) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for source in (existing, discovered):
        if not isinstance(source, list):
            continue
        for item in source:
            if not isinstance(item, dict):
                continue
            contact_type = str(item.get("type") or "").strip().lower()
            value = str(item.get("value") or "").strip()
            if not contact_type or not value:
                continue
            key = (contact_type, value.lower())
            if key in seen:
                continue
            seen.add(key)
            merged.append({"type": contact_type, "value": value})
    return merged


def _has_enough_valid_products(products: list[dict[str, Any]], max_results: int | None) -> bool:
    if max_results is None:
        return False
    try:
        required = int(max_results)
    except (TypeError, ValueError):
        return False
    if required <= 0:
        return False
    valid_count = sum(1 for product in products if _is_valid_search_product_payload(product))
    return valid_count >= required


def _is_valid_search_product_payload(product: dict[str, Any]) -> bool:
    if not isinstance(product, dict):
        return False
    if not str(product.get("title") or "").strip():
        return False
    product_url = str(product.get("productUrl") or product.get("product_url") or "").strip()
    parsed = urlparse(product_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    contacts = product.get("contacts")
    return isinstance(contacts, list) and any(
        isinstance(contact, dict)
        and str(contact.get("type") or "").strip().lower() in {"email", "telegram"}
        and str(contact.get("value") or "").strip()
        for contact in contacts
    )


def _contact_confidence(contacts: Any) -> int:
    if not isinstance(contacts, list) or not contacts:
        return 0
    types = {
        str(item.get("type") or "").strip().lower()
        for item in contacts
        if isinstance(item, dict) and str(item.get("value") or "").strip()
    }
    if "email" in types:
        return 100
    if "telegram" in types:
        return 80
    return 60


def _price_from_text(text: str) -> str | None:
    match = re.search(r"(?:[$]\s*|(?:USD|EUR|GBP)\s+)(\d[\d\s,.]*)", text, flags=re.IGNORECASE)
    if not match:
        return None
    raw = match.group(1).replace(" ", "")
    if raw.count(",") == 1 and "." not in raw:
        raw = raw.replace(",", ".")
    return raw.replace(",", "")


def _currency_from_text(text: str) -> str | None:
    normalized = text.upper()
    if "$" in text or "USD" in normalized:
        return "USD"
    if "\u20ac" in text or "EUR" in normalized:
        return "EUR"
    if "\u00a3" in text or "GBP" in normalized:
        return "GBP"
    return None


def _meaningful_query_terms(query_text: str) -> list[str]:
    query_without_site = re.sub(r"site:https?://[^\s]+", "", query_text, flags=re.IGNORECASE)
    terms = []
    for term in re.findall(r"[A-Za-z0-9-]+", query_without_site.lower()):
        if (len(term) >= 2 or term.isdigit()) and term not in {"site", "http", "https", "www", "com"}:
            terms.append(term)
    return terms


def _title_matches(title: str, query_terms: list[str]) -> bool:
    return any(_term_in_text(term, title) for term in query_terms)


def _score_candidate_link(title: str, url: str, query_terms: list[str]) -> int:
    normalized_url = url.lower()
    score = sum(2 for term in query_terms if _term_in_text(term, title))
    score += sum(1 for term in query_terms if _term_in_text(term, normalized_url))

    product_markers = (
        "/product/",
        "/products/",
        "/item/",
        "/items/",
        "/p/",
        "/dp/",
        "/sku/",
        "productid=",
        "product_id=",
    )
    if any(marker in normalized_url for marker in product_markers):
        score += 6

    non_product_markers = (
        "/category/",
        "/categories/",
        "/search",
        "/cart",
        "/basket",
        "/login",
        "/signin",
        "/sign-in",
        "/account",
        "/privacy",
        "/terms",
        "/help",
    )
    if any(marker in normalized_url for marker in non_product_markers):
        score -= 5
    return score


def _term_in_text(term: str, text: str) -> bool:
    normalized_term = term.lower()
    normalized_text = text.lower()
    if normalized_term in normalized_text:
        return True
    compact_term = re.sub(r"[^a-z0-9]+", "", normalized_term)
    compact_text = re.sub(r"[^a-z0-9]+", "", normalized_text)
    return bool(compact_term and compact_term in compact_text)
