import { ClipboardList, Moon, Plus, Search, Sun } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { listSearchRequests } from "./api";
import { statusClass, statusLabel } from "./components/format";
import { ProductDetailsPage } from "./pages/ProductDetailsPage";
import { RequestCatalogPage } from "./pages/RequestCatalogPage";
import { SearchRequestsPage } from "./pages/SearchRequestsPage";
import type { SearchRequestItem } from "./types";

type Theme = "light" | "dark";

function currentPath() {
  return window.location.pathname;
}

function activeSearchRequestId(path: string) {
  const requestMatch = path.match(/^\/search-requests\/([^/]+)\/products$/);
  return requestMatch?.[1] ?? null;
}

function route(path: string) {
  const productMatch = path.match(/^\/products\/([^/]+)$/);
  if (productMatch) {
    return <ProductDetailsPage productId={productMatch[1]} />;
  }
  const requestMatch = path.match(/^\/search-requests\/([^/]+)\/products$/);
  if (requestMatch) {
    return <RequestCatalogPage searchRequestId={requestMatch[1]} />;
  }
  return <SearchRequestsPage />;
}

export function App() {
  const [path, setPath] = useState(currentPath());
  const [theme, setTheme] = useState<Theme>(() => (localStorage.getItem("ui-theme") === "dark" ? "dark" : "light"));
  const [items, setItems] = useState<SearchRequestItem[]>([]);
  const [loadingSidebar, setLoadingSidebar] = useState(true);
  const [sidebarError, setSidebarError] = useState("");
  const activeId = useMemo(() => activeSearchRequestId(path), [path]);

  async function loadSidebar() {
    setSidebarError("");
    try {
      const response = await listSearchRequests();
      setItems(response.items);
    } catch (caught) {
      setSidebarError(caught instanceof Error ? caught.message : "Не удалось загрузить список запросов");
    } finally {
      setLoadingSidebar(false);
    }
  }

  useEffect(() => {
    void loadSidebar();
    const timer = window.setInterval(() => void loadSidebar(), 7000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    localStorage.setItem("ui-theme", theme);
  }, [theme]);

  useEffect(() => {
    const onPopState = () => setPath(currentPath());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  return (
    <main className="messenger-shell" data-theme={theme}>
      <aside className="messenger-sidebar" aria-label="Список поисковых запросов">
        <header className="sidebar-header">
          <a className="brand-mark" href="/" aria-label="Открыть список поисковых запросов">
            <ClipboardList aria-hidden="true" />
            <span>AI Sourcing</span>
          </a>
          <button
            type="button"
            className="theme-toggle"
            aria-label="Переключить тему"
            onClick={() => setTheme((current) => (current === "light" ? "dark" : "light"))}
          >
            {theme === "light" ? <Moon aria-hidden="true" /> : <Sun aria-hidden="true" />}
          </button>
        </header>

        <a className="new-chat-button action-button primary" href="/" aria-label="Создать новый поисковый запрос">
          <Plus aria-hidden="true" />
          Новый поиск
        </a>

        <div className="sidebar-search" role="search">
          <Search aria-hidden="true" />
          <span>История запросов</span>
        </div>

        {loadingSidebar && (
          <div className="sidebar-state" role="status">
            <span className="spinner" aria-hidden="true" />
            Загрузка
          </div>
        )}
        {sidebarError && <p className="sidebar-state error-text">{sidebarError}</p>}
        {!loadingSidebar && !sidebarError && items.length === 0 && <p className="sidebar-state">Пока нет запросов</p>}

        <nav className="sidebar-items" aria-label="Запросы">
          {items.map((item) => (
            <a
              key={item.id}
              className={`sidebar-item ${activeId === item.id ? "active" : ""}`}
              href={`/search-requests/${item.id}/products`}
              aria-current={activeId === item.id ? "page" : undefined}
            >
              <span className="sidebar-avatar">{item.queryText.slice(0, 1).toUpperCase()}</span>
              <span className="sidebar-item-body">
                <span className="sidebar-item-title">{item.queryText}</span>
                <span className="sidebar-item-meta">
                  <span className={statusClass(item.status)}>{statusLabel(item.status)}</span>
                  <span>{item.productsCount} товаров</span>
                </span>
              </span>
            </a>
          ))}
        </nav>
      </aside>

      <section className="messenger-main" aria-label="Рабочая область">
        {route(path)}
      </section>
    </main>
  );
}
