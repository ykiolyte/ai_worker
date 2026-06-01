import { ArrowRight, Eye } from "lucide-react";
import { useEffect, useState } from "react";
import { getSearchRequest, listProducts } from "../api";
import { formatDuration, formatNullable, formatPrice, formatPriceDelta, formatPriceRank, progressPercent, ratingLabel, remainingHint, stageLabel, statusClass, statusLabel } from "../components/format";
import type { ProductCard, SearchRequestItem } from "../types";

interface Props {
  searchRequestId: string;
}

export function RequestCatalogPage({ searchRequestId }: Props) {
  const [items, setItems] = useState<ProductCard[]>([]);
  const [duplicates, setDuplicates] = useState<ProductCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [searchRequest, setSearchRequest] = useState<SearchRequestItem>();
  const [catalogFilter, setCatalogFilter] = useState("all");
  const [selectedCommonFilters, setSelectedCommonFilters] = useState<string[]>([]);
  const [selectedAttributeFilters, setSelectedAttributeFilters] = useState<Array<{ name: string; value: string }>>([]);
  const [priceMinimum, setPriceMinimum] = useState("");
  const [priceMaximum, setPriceMaximum] = useState("");

  async function load(silent = false) {
    if (!silent) {
      setLoading(true);
    }
    setError("");
    try {
      const [request, response] = await Promise.all([getSearchRequest(searchRequestId), listProducts(searchRequestId)]);
      setSearchRequest(request);
      setItems(response.items);
      setDuplicates(response.duplicates ?? []);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось загрузить каталог");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [searchRequestId]);

  useEffect(() => {
    if (!searchRequest || (searchRequest.status !== "queued" && searchRequest.status !== "running")) {
      return;
    }
    const timer = window.setInterval(() => {
      void load(true);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [searchRequest?.status, searchRequestId]);

  const pageSize = 20;
  const catalogItems = catalogFilter === "duplicates" ? duplicates : items;
  const filteredItems = catalogItems.filter((product) => {
    if (catalogFilter === "duplicates") {
      return true;
    }
    const contacts = product.contacts ?? [];
    const isDemo = product.attributes.demo === "true" || product.sourceDomain === "demo.local";
    if (catalogFilter === "with-contact") {
      return contacts.length > 0;
    }
    if (catalogFilter === "without-contact") {
      return contacts.length === 0;
    }
    if (catalogFilter === "demo") {
      return isDemo;
    }
    if (catalogFilter === "email") {
      return contacts.some((contact) => contact.contactType === "email");
    }
    if (catalogFilter === "telegram") {
      return contacts.some((contact) => contact.contactType === "telegram");
    }
    return matchesSourcingFilters(product, selectedCommonFilters, selectedAttributeFilters, priceMinimum, priceMaximum);
  });
  const visible = filteredItems.slice((page - 1) * pageSize, page * pageSize);
  const madeInChinaItems = visible.filter((product) => product.attributes.sourcePlatform === "made-in-china");
  const regularItems = visible.filter((product) => product.attributes.sourcePlatform !== "made-in-china");
  const missingFields = searchRequest?.missingFields ?? [];
  const clarifyingQuestions = searchRequest?.clarifyingQuestions ?? [];
  const commonFilters = searchRequest?.commonFilters ?? [];
  const productAttributes = searchRequest?.productAttributes ?? [];
  const sourcingGuidance = searchRequest?.sourcingGuidance ?? {};
  const filters = [
    ["all", "Все"],
    ["with-contact", "С контактом"],
    ["without-contact", "Без контакта"],
    ["demo", "Демо"],
    ["duplicates", `Дубликаты (${duplicates.length})`],
    ["email", "Email"],
    ["telegram", "Telegram"],
  ];
  const hasSourcingFilters = selectedCommonFilters.length > 0 || selectedAttributeFilters.length > 0 || priceMinimum || priceMaximum;
  const toggleCommonFilter = (filter: string) => {
    setSelectedCommonFilters((current) => current.includes(filter) ? current.filter((item) => item !== filter) : [...current, filter]);
    setPage(1);
  };
  const toggleAttributeFilter = (name: string, value: string) => {
    setSelectedAttributeFilters((current) => {
      const exists = current.some((item) => item.name === name && item.value === value);
      return exists ? current.filter((item) => item.name !== name || item.value !== value) : [...current, { name, value }];
    });
    setPage(1);
  };
  const clearSourcingFilters = () => {
    setSelectedCommonFilters([]);
    setSelectedAttributeFilters([]);
    setPriceMinimum("");
    setPriceMaximum("");
    setPage(1);
  };
  const renderProductCard = (product: ProductCard) => {
    const contacts = product.contacts ?? [];
    const primaryContact = contacts[0];
    const isDemo = product.attributes.demo === "true" || product.sourceDomain === "demo.local";
    const isDuplicate = product.isDuplicate === true || catalogFilter === "duplicates";
    const isMadeInChina = product.attributes.sourcePlatform === "made-in-china";
    const previewImage = product.images[0];
    return (
      <article className={`product-card attachment-card message-bubble ${isDemo ? "product-card-demo" : ""}`} key={product.id}>
        <div className="preview-media" aria-label="Превью товара">
          {previewImage ? <img src={previewImage} alt="" /> : <span>{product.title.slice(0, 1).toUpperCase()}</span>}
        </div>
        <div className="attachment-body">
          <div className="card-title-row">
            <h3>{product.title}</h3>
            {product.supplierComparison && (
              <span className={`supplier-rating rating-${product.supplierComparison.ratingLabel}`}>
                {product.supplierComparison.overallRating}/100
              </span>
            )}
            {isMadeInChina && <span className="source-badge made-in-china-badge">Made-in-China</span>}
            {isDemo && <span className="demo-badge">Демо</span>}
            {isDuplicate && <span className="demo-badge">Дубликат</span>}
          </div>
          <p>{formatPrice(product.price, product.currency) || product.priceRange || stringAttribute(product, "madeInChinaPriceText") || "Цена не найдена"}</p>
          {product.moq && <p>MOQ: {product.moq}</p>}
          <p>{formatNullable(product.supplierName, "Поставщик не указан")}</p>
          {(product.supplierBadges ?? []).length > 0 && (
            <div className="chip-row" aria-label="Supplier badges">
              {(product.supplierBadges ?? []).map((badge) => <span className="source-badge" key={badge}>{badge}</span>)}
            </div>
          )}
          {product.fitScore && (
            <p className="fit-score">Fit {Math.round(Number(product.fitScore) * 100)}% · Satisfies {(product.matchedRequirements ?? []).length} requirements</p>
          )}
          {product.fitSummary && <p>{product.fitSummary}</p>}
          {isMadeInChina && (
            <div className="made-in-china-fields" aria-label="Made-in-China параметры">
              {stringAttribute(product, "moq") && <span>MOQ: {stringAttribute(product, "moq")}</span>}
              {stringAttribute(product, "supplierLocation") && <span>{stringAttribute(product, "supplierLocation")}</span>}
              {stringAttribute(product, "businessType") && <span>{stringAttribute(product, "businessType")}</span>}
              {stringAttribute(product, "inquiryUrl") && (
                <a href={stringAttribute(product, "inquiryUrl")} target="_blank" rel="noopener noreferrer">
                  Inquiry
                </a>
              )}
            </div>
          )}
          {product.supplierComparison && (
            <section className="comparison-metrics" aria-label="Supplier comparison metrics">
              <strong>{ratingLabel(product.supplierComparison.ratingLabel)}</strong>
              <span>{formatPriceRank(product.supplierComparison.priceRank, product.supplierComparison.comparedProductsCount)}</span>
              <span>{formatPriceDelta(product.supplierComparison.priceDeltaPercent)}</span>
              <span>Price {product.supplierComparison.metrics.priceScore}</span>
              <span>Contact {product.supplierComparison.metrics.contactabilityScore}</span>
              <span>Response {product.supplierComparison.metrics.responseScore}</span>
              <span>Data {product.supplierComparison.metrics.dataCompletenessScore}</span>
              <span>Source {product.supplierComparison.metrics.sourceTraceabilityScore}</span>
            </section>
          )}
          <p className="contact-summary">
            {primaryContact ? `${primaryContact.contactType}: ${primaryContact.contactValue}` : product.attributes.inquiryUrl ? "Inquiry доступен" : "Контакт не найден"}
          </p>
          {isDuplicate && product.duplicateReason && <p className="muted">{product.duplicateReason}</p>}
          <div className="product-card-actions">
            {!isDuplicate && (
              <a className="action-button primary" href={`/products/${product.id}`} aria-label={`Открыть карточку товара: ${product.title}`}>
                <Eye aria-hidden="true" />
                Открыть карточку
              </a>
            )}
            {!isDemo && (
              <a className="action-button secondary" href={product.productUrl} target="_blank" rel="noopener noreferrer">
                Открыть источник <ArrowRight aria-hidden="true" />
              </a>
            )}
          </div>
        </div>
      </article>
    );
  };

  return (
    <section className="workspace chat-workspace">
      <header className="chat-header">
        <div>
          <h2>Каталог товаров</h2>
          <p>{searchRequest ? searchRequest.queryText : "Результаты выбранного запроса"}</p>
        </div>
      </header>

      {searchRequest && (searchRequest.status === "queued" || searchRequest.status === "running") && (
        <div className="system-message progress-panel" role="status">
          <span>
            <span className="spinner" aria-hidden="true" />
            <span className={statusClass(searchRequest.status)}>{statusLabel(searchRequest.status)}</span>{" "}
            {stageLabel(searchRequest.status, searchRequest.productsCount)}. Найдено товаров: {searchRequest.productsCount}
          </span>
          <div className="progress-bar" aria-label="Прогресс поиска">
            <span style={{ width: `${progressPercent(searchRequest.status, searchRequest.createdAt, searchRequest.completedAt)}%` }} />
          </div>
          <small>Осталось {remainingHint(searchRequest.status, searchRequest.createdAt)}</small>
        </div>
      )}
      {searchRequest?.durationSeconds !== undefined && searchRequest?.durationSeconds !== null && (
        <p className="system-message">Поиск занял: {formatDuration(searchRequest.durationSeconds)}</p>
      )}
      {searchRequest && (
        <section className="sourcing-guidance bubble-card" aria-label="Sourcing guidance">
          <div className="dashboard-grid">
            <article className="metric-card bubble-card">
              <span>Поставщики</span>
              <strong>{searchRequest.suppliersCount ?? 0}</strong>
            </article>
            <article className="metric-card bubble-card">
              <span>Товары</span>
              <strong>{searchRequest.productsCount}</strong>
            </article>
          </div>
          {missingFields.length > 0 && <p>Не хватает: {missingFields.join(", ")}</p>}
          {clarifyingQuestions.length > 0 && <ul>{clarifyingQuestions.map((question) => <li key={question}>{question}</li>)}</ul>}
          {commonFilters.length > 0 && <div className="chip-row">{commonFilters.map((filter) => <span className="source-badge" key={filter}>{filter}</span>)}</div>}
          {productAttributes.length > 0 && (
            <div className="chip-row">
              {productAttributes.flatMap((facet) => facet.values.map((value) => (
                <span className="source-badge" key={`${facet.name}-${value}`}>{facet.name}: {value}</span>
              )))}
            </div>
          )}
          {sourcingGuidance.riskWarnings?.length ? <p>Риски: {sourcingGuidance.riskWarnings.join("; ")}</p> : null}
          {sourcingGuidance.negotiationTips?.length ? <p>Переговоры: {sourcingGuidance.negotiationTips.join("; ")}</p> : null}
        </section>
      )}
      {loading && (
        <p className="system-message" role="status">
          <span className="spinner" aria-hidden="true" />
          Загрузка каталога
        </p>
      )}
      {error && (
        <div className="error-summary system-message" role="alert">
          <strong>Не удалось загрузить каталог</strong>
          <details>
            <summary>Подробнее</summary>
            <code>{error}</code>
          </details>
        </div>
      )}
      {!loading && !error && items.length === 0 && <p className="system-message">Товары не найдены</p>}

      {!loading && !error && (items.length > 0 || duplicates.length > 0) && (
        <>
          <div className="catalog-filters" aria-label="Фильтры каталога">
            {filters.map(([value, label]) => (
              <button
                key={value}
                type="button"
                className={catalogFilter === value ? "active action-button" : "action-button secondary"}
                onClick={() => {
                  setCatalogFilter(value);
                  setPage(1);
                }}
              >
                {label}
              </button>
            ))}
          </div>
          <section className="sourcing-filter-panel bubble-card" aria-label="Sourcing filters">
            <div className="price-filter-row">
              <span>US$</span>
              <input aria-label="Minimum" placeholder="Minimum" value={priceMinimum} onChange={(event) => { setPriceMinimum(event.target.value); setPage(1); }} />
              <span>-</span>
              <input aria-label="Maximum" placeholder="Maximum" value={priceMaximum} onChange={(event) => { setPriceMaximum(event.target.value); setPage(1); }} />
            </div>
            {commonFilters.length > 0 && (
              <div className="facet-row">
                <strong>Commonly Used:</strong>
                <div className="chip-row">
                  {commonFilters.map((filter) => (
                    <button key={filter} type="button" className={selectedCommonFilters.includes(filter) ? "source-badge selected-filter" : "source-badge"} onClick={() => toggleCommonFilter(filter)}>
                      {filter}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {productAttributes.map((facet) => (
              <div className="facet-row" key={facet.name}>
                <strong>{facet.name}:</strong>
                {facet.summary && <p>{facet.summary}</p>}
                <div className="chip-row">
                  {facet.values.map((value) => {
                    const selected = selectedAttributeFilters.some((item) => item.name === facet.name && item.value === value);
                    return (
                      <button key={`${facet.name}-${value}`} type="button" className={selected ? "source-badge selected-filter" : "source-badge"} onClick={() => toggleAttributeFilter(facet.name, value)}>
                        {value}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
            {hasSourcingFilters && <button className="action-button secondary" type="button" onClick={clearSourcingFilters}>Clear filters</button>}
          </section>
        </>
      )}

      {!loading && !error && catalogItems.length > 0 && filteredItems.length === 0 && (
        <p className="system-message">Нет товаров по выбранным фильтрам. <button className="link-button" type="button" onClick={clearSourcingFilters}>Сбросить фильтры</button></p>
      )}

      <div className="catalog-source-columns">
        <section className="source-column regular-column" aria-label="Остальные источники">
          <header>
            <h3>Остальные источники</h3>
            <span>{regularItems.length}</span>
          </header>
          <div className="product-grid message-list">
            {regularItems.map(renderProductCard)}
            {regularItems.length === 0 && <p className="system-message">Нет результатов в этой колонке</p>}
          </div>
        </section>
        <section className="source-column made-in-china-column" aria-label="Made-in-China">
          <header>
            <h3>Made-in-China</h3>
            <span>{madeInChinaItems.length}</span>
          </header>
          <div className="product-grid message-list">
            {madeInChinaItems.map(renderProductCard)}
            {madeInChinaItems.length === 0 && <p className="system-message">Нет результатов Made-in-China</p>}
          </div>
        </section>
      </div>

      {filteredItems.length > pageSize && (
        <nav className="pagination" aria-label="Пагинация каталога">
          <button className="action-button secondary" type="button" disabled={page === 1} onClick={() => setPage((current) => current - 1)}>
            Назад
          </button>
          <span>{page}</span>
          <button
            className="action-button secondary"
            type="button"
            disabled={page * pageSize >= filteredItems.length}
            onClick={() => setPage((current) => current + 1)}
          >
            Следующая
          </button>
        </nav>
      )}
    </section>
  );
}

function matchesSourcingFilters(
  product: ProductCard,
  commonFilters: string[],
  attributeFilters: Array<{ name: string; value: string }>,
  priceMinimum: string,
  priceMaximum: string,
) {
  if (!matchesPrice(product, priceMinimum, priceMaximum)) {
    return false;
  }
  if (!commonFilters.every((filter) => matchesCommonFilter(product, filter))) {
    return false;
  }
  return attributeFilters.every((filter) => matchesAttributeFilter(product, filter.name, filter.value));
}

function matchesPrice(product: ProductCard, minimum: string, maximum: string) {
  const min = Number(minimum);
  const max = Number(maximum);
  const hasMin = minimum.trim() !== "" && Number.isFinite(min);
  const hasMax = maximum.trim() !== "" && Number.isFinite(max);
  if (!hasMin && !hasMax) {
    return true;
  }
  const price = numericPrice(product);
  if (price === null) {
    return false;
  }
  return (!hasMin || price >= min) && (!hasMax || price <= max);
}

function numericPrice(product: ProductCard) {
  const values = [product.price, product.priceRange, stringAttribute(product, "madeInChinaPriceText")];
  for (const value of values) {
    const match = String(value ?? "").replace(/,/g, "").match(/\d+(?:\.\d+)?/);
    if (match) {
      return Number(match[0]);
    }
  }
  return null;
}

function matchesCommonFilter(product: ProductCard, filter: string) {
  const lowered = filter.toLowerCase();
  if (lowered.includes("customization")) {
    return product.supportsCustomization === true || productMatchesText(product, "custom");
  }
  if (lowered.includes("sample")) {
    return product.sampleAvailable === true || productMatchesText(product, "sample");
  }
  if (lowered.includes("manufacturer")) {
    return productMatchesText(product, "manufacturer") || productMatchesText(product, "factory");
  }
  if (lowered.includes("price")) {
    return numericPrice(product) !== null;
  }
  return productMatchesText(product, filter);
}

function matchesAttributeFilter(product: ProductCard, name: string, value: string) {
  const direct = stringAttribute(product, name) || stringAttribute(product, toCamelCase(name));
  if (direct && direct.toLowerCase().includes(value.toLowerCase())) {
    return true;
  }
  return productMatchesText(product, value);
}

function productMatchesText(product: ProductCard, value: string) {
  return productSearchText(product).includes(value.toLowerCase());
}

function productSearchText(product: ProductCard) {
  return [
    product.title,
    product.description,
    product.supplierName,
    product.supplierCountry,
    product.supplierCity,
    product.priceRange,
    product.moq,
    ...(product.supplierBadges ?? []),
    ...Object.values(product.attributes ?? {}).map((value) => typeof value === "string" ? value : JSON.stringify(value)),
  ].join(" ").toLowerCase();
}

function stringAttribute(product: ProductCard, key: string) {
  const value = product.attributes?.[key];
  return typeof value === "string" ? value : "";
}

function toCamelCase(value: string) {
  const words = value.match(/[A-Za-z0-9]+/g) ?? [];
  return words.map((word, index) => index === 0 ? word.toLowerCase() : word.slice(0, 1).toUpperCase() + word.slice(1).toLowerCase()).join("");
}
