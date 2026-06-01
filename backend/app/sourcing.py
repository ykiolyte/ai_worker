from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .domain import is_valid_email, is_valid_telegram, validate_url


def _alias_config() -> ConfigDict:
    return ConfigDict(populate_by_name=True, extra="ignore")


class NormalizedIntentSchema(BaseModel):
    model_config = _alias_config()

    raw_query: str | None = Field(default=None, alias="rawQuery")
    product_category: str | None = Field(default=None, alias="productCategory")
    target_market: str | None = Field(default=None, alias="targetMarket")
    quantity: str | None = None
    budget: str | None = None
    certifications: list[str] | None = None
    supplier_preference: str | None = Field(default=None, alias="supplierPreference")
    must_have: list[str] | None = Field(default=None, alias="mustHave")
    nice_to_have: list[str] | None = Field(default=None, alias="niceToHave")


class ProductAttributeFacetSchema(BaseModel):
    model_config = _alias_config()

    name: str
    values: list[str] = Field(default_factory=list)
    summary: str | None = None

    @field_validator("name")
    @classmethod
    def name_required(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("facet name is required")
        return normalized


class MatchedRequirementSchema(BaseModel):
    model_config = _alias_config()

    requirement: str
    evidence: str

    @field_validator("requirement", "evidence")
    @classmethod
    def text_required(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("requirement and evidence are required")
        return normalized


class SupplierContactSchema(BaseModel):
    model_config = _alias_config()

    type: str
    value: str

    @field_validator("type")
    @classmethod
    def supported_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"email", "telegram"}:
            raise ValueError("unsupported contact type")
        return normalized

    @field_validator("value")
    @classmethod
    def valid_contact(cls, value: str, info) -> str:
        normalized = value.strip()
        contact_type = (info.data.get("type") or "").lower()
        if contact_type == "email" and not is_valid_email(normalized):
            raise ValueError("email contact must be valid")
        if contact_type == "telegram" and not is_valid_telegram(normalized):
            raise ValueError("telegram contact must be valid")
        return normalized


class SourcingGuidanceSchema(BaseModel):
    model_config = _alias_config()

    quality_indicators: list[str] = Field(default_factory=list, alias="qualityIndicators")
    negotiation_tips: list[str] = Field(default_factory=list, alias="negotiationTips")
    risk_warnings: list[str] = Field(default_factory=list, alias="riskWarnings")
    cross_border_notes: list[str] = Field(default_factory=list, alias="crossBorderNotes")
    related_queries: list[str] = Field(default_factory=list, alias="relatedQueries")


class SourcingProductSchema(BaseModel):
    model_config = _alias_config()

    title: str
    product_url: str = Field(alias="productUrl")
    price: str | float | int | None = None
    price_range: str | None = Field(default=None, alias="priceRange")
    currency: str | None = None
    moq: str | None = None
    supplier_name: str | None = Field(default=None, alias="supplierName")
    supplier_country: str | None = Field(default=None, alias="supplierCountry")
    supplier_city: str | None = Field(default=None, alias="supplierCity")
    supplier_badges: list[str] = Field(default_factory=list, alias="supplierBadges")
    is_verified_supplier: bool = Field(default=False, alias="isVerifiedSupplier")
    is_audited_supplier: bool = Field(default=False, alias="isAuditedSupplier")
    supports_customization: bool = Field(default=False, alias="supportsCustomization")
    sample_available: bool = Field(default=False, alias="sampleAvailable")
    fit_score: float | None = Field(default=None, ge=0, le=1, alias="fitScore")
    fit_summary: str | None = Field(default=None, alias="fitSummary")
    matched_requirements: list[MatchedRequirementSchema] = Field(default_factory=list, alias="matchedRequirements")
    missing_requirements: list[str] = Field(default_factory=list, alias="missingRequirements")
    contacts: list[SupplierContactSchema] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    description: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title")
    @classmethod
    def title_required(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("title is required")
        return normalized

    @field_validator("product_url")
    @classmethod
    def valid_product_url(cls, value: str) -> str:
        normalized = value.strip()
        if not validate_url(normalized):
            raise ValueError("productUrl must be a valid URL")
        return normalized

    @field_validator("images")
    @classmethod
    def valid_images(cls, value: list[str]) -> list[str]:
        for image in value:
            if not validate_url(str(image)):
                raise ValueError("images must be valid URLs")
        return value


class SourcingSearchOutputSchema(BaseModel):
    model_config = _alias_config()

    normalized_intent: NormalizedIntentSchema = Field(default_factory=NormalizedIntentSchema, alias="normalizedIntent")
    missing_fields: list[str] = Field(default_factory=list, alias="missingFields")
    clarifying_questions: list[str] = Field(default_factory=list, alias="clarifyingQuestions")
    common_filters: list[str] = Field(default_factory=list, alias="commonFilters")
    product_attributes: list[ProductAttributeFacetSchema] = Field(default_factory=list, alias="productAttributes")
    products: list[SourcingProductSchema] = Field(default_factory=list)
    sourcing_guidance: SourcingGuidanceSchema = Field(default_factory=SourcingGuidanceSchema, alias="sourcingGuidance")

    @classmethod
    def from_agent_payload(cls, payload: dict[str, Any]) -> "SourcingSearchOutputSchema":
        return cls.model_validate(payload or {})


@dataclass(frozen=True)
class ProductCandidate:
    title: str
    product_url: str
    supplier_name: str | None = None
    price_text: str | None = None
    moq_text: str | None = None
    supplier_badges: list[str] = field(default_factory=list)
    supplier_country: str | None = None
    supplier_city: str | None = None
    is_verified_supplier: bool = False
    is_audited_supplier: bool = False
    supports_customization: bool = False
    sample_available: bool = False
    contacts: list[dict[str, str]] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    description: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    source_url: str = ""
    source_domain: str = ""
    extraction_method: str = "public_page"
    confidence: float = 0.0
    field_evidence: dict[str, Any] = field(default_factory=dict)


class ProductNormalizer:
    def normalize(self, candidate: ProductCandidate) -> dict[str, Any]:
        parsed = urlparse(candidate.product_url)
        source_domain = candidate.source_domain or parsed.netloc
        attributes = dict(candidate.attributes)
        attributes.setdefault("sourceDomain", source_domain)
        attributes.setdefault("sourceUrl", candidate.source_url or candidate.product_url)
        attributes.setdefault("extractionMethod", candidate.extraction_method)
        attributes.setdefault("confidence", str(candidate.confidence))
        if candidate.field_evidence:
            attributes.setdefault("fieldEvidence", candidate.field_evidence)
        price_range = candidate.price_text if candidate.price_text and not _looks_numeric(candidate.price_text) else None
        price = _numeric_price_text(candidate.price_text) if candidate.price_text and _looks_numeric(candidate.price_text) else None
        return {
            "title": candidate.title,
            "productUrl": candidate.product_url,
            "price": price,
            "priceRange": price_range,
            "moq": candidate.moq_text,
            "supplierName": candidate.supplier_name,
            "supplierCountry": candidate.supplier_country,
            "supplierCity": candidate.supplier_city,
            "supplierBadges": list(candidate.supplier_badges),
            "isVerifiedSupplier": candidate.is_verified_supplier,
            "isAuditedSupplier": candidate.is_audited_supplier,
            "supportsCustomization": candidate.supports_customization,
            "sampleAvailable": candidate.sample_available,
            "contacts": list(candidate.contacts),
            "images": list(candidate.images),
            "description": candidate.description,
            "attributes": attributes,
            "rawProvenance": {
                "source_url": candidate.source_url or candidate.product_url,
                "source_domain": source_domain,
                "extracted_at": datetime.now(timezone.utc).isoformat(),
                "extraction_method": candidate.extraction_method,
                "confidence": candidate.confidence,
                "field_evidence": candidate.field_evidence,
            },
        }


class ProductFitEvaluator:
    def evaluate(self, intent: dict[str, Any], product: dict[str, Any]) -> dict[str, Any]:
        text = " ".join(
            str(value)
            for value in [
                product.get("title"),
                product.get("description"),
                product.get("supplierName"),
                " ".join(product.get("supplierBadges") or []),
                product.get("attributes", {}),
            ]
        ).lower()
        score = 0.35
        matched: list[dict[str, str]] = []
        missing: list[str] = []

        supplier_preference = str(intent.get("supplierPreference") or intent.get("supplier_preference") or "").lower()
        if supplier_preference == "manufacturer_first":
            if any(marker in text for marker in ("manufacturer", "factory", "oem", "odm")):
                score += 0.2
                matched.append({"requirement": "manufacturer-first supplier", "evidence": "Manufacturer/factory evidence found"})
            else:
                missing.append("No manufacturer/factory evidence found")

        for requirement in intent.get("mustHave") or intent.get("must_have") or []:
            req = str(requirement).strip()
            if req and req.lower() in text:
                score += 0.1
                matched.append({"requirement": req, "evidence": f"Product text contains {req}"})
            elif req:
                missing.append(req)

        for certification in intent.get("certifications") or []:
            cert = str(certification).strip()
            if cert and _token_present(cert, text):
                score += 0.08
                matched.append({"requirement": cert, "evidence": f"Public text mentions {cert}"})
            elif cert:
                missing.append(f"No public certification evidence found for {cert}")

        if product.get("supportsCustomization") or any("custom" in badge.lower() for badge in product.get("supplierBadges") or []):
            score += 0.08
            matched.append({"requirement": "customization support", "evidence": "Customization badge or field found"})
            product["supportsCustomization"] = True

        score = max(0.0, min(1.0, score))
        return {
            "fitScore": round(score, 4),
            "fitSummary": _fit_summary(score, matched, missing),
            "matchedRequirements": matched,
            "missingRequirements": missing,
        }


def _looks_numeric(value: str) -> bool:
    import re

    normalized = value.strip().replace(",", "")
    return bool(re.fullmatch(r"(?:us\$|\$|usd|eur|cny|rmb)?\s*\d+(?:\.\d+)?", normalized, flags=re.I))


def _numeric_price_text(value: str | None) -> str | None:
    if not value:
        return None
    import re

    match = re.search(r"\d+(?:\.\d+)?", value.replace(",", ""))
    return match.group(0) if match else None


def _fit_summary(score: float, matched: list[dict[str, str]], missing: list[str]) -> str:
    if matched and missing:
        return f"Matches {len(matched)} sourcing signals, with {len(missing)} missing requirements to verify."
    if matched:
        return f"Matches {len(matched)} sourcing signals from public evidence."
    return "Limited public evidence; verify supplier fit before contacting."


def _token_present(token: str, text: str) -> bool:
    import re

    return bool(re.search(rf"(?<![a-z0-9]){re.escape(token.lower())}(?![a-z0-9])", text.lower()))
