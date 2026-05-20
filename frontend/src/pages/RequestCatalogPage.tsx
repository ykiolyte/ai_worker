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
    return true;
  });
  const visible = filteredItems.slice((page - 1) * pageSize, page * pageSize);
  const filters = [
    ["all", "Все"],
    ["with-contact", "С контактом"],
    ["without-contact", "Без контакта"],
    ["demo", "Демо"],
    ["duplicates", `Дубликаты (${duplicates.length})`],
    ["email", "Email"],
    ["telegram", "Telegram"],
  ];

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
      )}

      <div className="product-grid message-list">
        {visible.map((product) => {
          const contacts = product.contacts ?? [];
          const primaryContact = contacts[0];
          const isDemo = product.attributes.demo === "true" || product.sourceDomain === "demo.local";
          const isDuplicate = product.isDuplicate === true || catalogFilter === "duplicates";
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
                  {isDemo && <span className="demo-badge">Демо</span>}
                  {isDuplicate && <span className="demo-badge">Дубликат</span>}
                </div>
                <p>{formatPrice(product.price, product.currency) || "Цена не найдена"}</p>
                <p>{formatNullable(product.supplierName, "Поставщик не указан")}</p>
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
                  {primaryContact ? `${primaryContact.contactType}: ${primaryContact.contactValue}` : "Контакт не найден"}
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
                    <a className="action-button secondary" href={product.productUrl} target="_blank" rel="noreferrer">
                    Открыть источник <ArrowRight aria-hidden="true" />
                    </a>
                  )}
                </div>
              </div>
            </article>
          );
        })}
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
