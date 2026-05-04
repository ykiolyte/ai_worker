import { Eye, Plus, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { createSearchRequest, listSearchRequests } from "../api";
import { formatDuration, progressPercent, remainingHint, stageLabel, statusClass, statusLabel } from "../components/format";
import type { SearchRequestItem } from "../types";

export function SearchRequestsPage() {
  const [items, setItems] = useState<SearchRequestItem[]>([]);
  const [queryText, setQueryText] = useState("");
  const [maxResults, setMaxResults] = useState(5);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load(silent = false) {
    if (!silent) {
      setLoading(true);
    }
    setError("");
    try {
      const response = await listSearchRequests();
      setItems(response.items);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось загрузить поисковые запросы");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const hasActiveSearch = items.some((item) => item.status === "queued" || item.status === "running");
  const awaitingReplies = items.reduce((sum, item) => sum + (item.awaitingRepliesCount ?? 0), 0);
  const receivedReplies = items.reduce((sum, item) => sum + (item.receivedRepliesCount ?? 0), 0);

  useEffect(() => {
    if (!hasActiveSearch) {
      return;
    }
    const timer = window.setInterval(() => {
      void load(true);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [hasActiveSearch]);

  const activeCount = items.filter((item) => item.status === "queued" || item.status === "running").length;
  const foundProducts = items.reduce((sum, item) => sum + item.productsCount, 0);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const created = await createSearchRequest(queryText.trim(), maxResults);
    setQueryText("");
    setItems((current) => [created, ...current]);
  }

  return (
    <section className="workspace chat-workspace">
      <header className="chat-header">
        <div>
          <h2>Поисковые запросы</h2>
          <p>Создавайте запросы и наблюдайте за работой агента как за диалогом.</p>
        </div>
        <span className="toolbar-action">
          <Plus aria-hidden="true" />
          Новый запрос
        </span>
      </header>

      <div className="system-message demo-mode-banner">
        <strong>Демо-режим</strong>
        <span>В каждом каталоге добавляется отдельная тестовая карточка с демонстрационным контактом.</span>
      </div>

      <div className="dashboard-grid" aria-label="Сводка поиска">
        <article className="metric-card bubble-card">
          <span>Активные поиски</span>
          <strong>{activeCount}</strong>
        </article>
        <article className="metric-card bubble-card">
          <span>Найдено товаров</span>
          <strong>{foundProducts}</strong>
        </article>
        <article className="metric-card bubble-card">
          <span>Ожидают ответа</span>
          <strong>{awaitingReplies}</strong>
        </article>
        <article className="metric-card bubble-card">
          <span>Получены ответы</span>
          <strong>{receivedReplies}</strong>
        </article>
      </div>

      <form className="inline-form bubble-card" onSubmit={submit}>
        <label>
          <span>Текст запроса</span>
          <input value={queryText} onChange={(event) => setQueryText(event.target.value)} minLength={3} maxLength={1000} />
        </label>
        <label>
          <span>Максимум результатов</span>
          <input
            type="number"
            value={maxResults}
            onChange={(event) => setMaxResults(Number(event.target.value))}
            min={1}
            max={50}
          />
        </label>
        <button className="action-button primary" type="submit" disabled={queryText.trim().length < 3}>
          <Search aria-hidden="true" />
          Запустить поиск
        </button>
      </form>

      {loading && (
        <p className="system-message" role="status">
          <span className="spinner" aria-hidden="true" />
          Загрузка поисковых запросов
        </p>
      )}
      {error && (
        <div className="error-summary system-message" role="alert">
          <strong>Не удалось загрузить поисковые запросы</strong>
          <details>
            <summary>Подробнее</summary>
            <code>{error}</code>
          </details>
        </div>
      )}
      {!loading && !error && items.length === 0 && <p className="system-message">Пока нет поисковых запросов</p>}

      {!loading && !error && items.length > 0 && (
        <div className="message-list" aria-label="История поисковых запросов">
          {items.map((item) => (
            <article className="message-bubble search-request-bubble" key={item.id}>
              <div className="message-bubble-main">
                <a className="table-link" href={`/search-requests/${item.id}/products`}>
                  {item.queryText}
                </a>
                <span className={statusClass(item.status)}>{statusLabel(item.status)}</span>
                <small className="stage-label">{stageLabel(item.status, item.productsCount)}</small>
                {(item.status === "queued" || item.status === "running") && (
                  <div className="progress-cell">
                    <div className="progress-bar" aria-label="Прогресс поиска">
                      <span style={{ width: `${progressPercent(item.status, item.createdAt, item.completedAt)}%` }} />
                    </div>
                    <small>{stageLabel(item.status, item.productsCount)}. Осталось {remainingHint(item.status, item.createdAt)}</small>
                  </div>
                )}
              </div>
              <div className="message-bubble-meta">
                <span>Лимит: {item.maxResults}</span>
                <span>Товары: {item.productsCount}</span>
                <span>Поиск занял: {formatDuration(item.durationSeconds)}</span>
                <span>{new Date(item.createdAt).toLocaleString()}</span>
              </div>
              <a className="action-button secondary" href={`/search-requests/${item.id}/products`} aria-label={`Открыть каталог: ${item.queryText}`}>
                <Eye aria-hidden="true" />
                Открыть каталог
              </a>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
