import type { GmailSyncOptions, InboundMessagePayload, ProductDetail, SearchRequestItem, SupplierMessagePreferences } from "./types";

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL;
const browserApiBaseUrl = `${window.location.protocol}//${window.location.hostname}:8000/api`;
const API_BASE_URL =
  window.location.hostname === "host.docker.internal"
    ? browserApiBaseUrl
    : configuredApiBaseUrl || browserApiBaseUrl;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "content-type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: "Не удалось выполнить запрос" }));
    throw new Error(detail.detail ?? "Не удалось выполнить запрос");
  }
  return response.json() as Promise<T>;
}

export function listSearchRequests() {
  return request<{ items: SearchRequestItem[] }>("/search-requests");
}

export function getSearchRequest(searchRequestId: string) {
  return request<SearchRequestItem>(`/search-requests/${searchRequestId}`);
}

export function createSearchRequest(queryText: string, maxResults: number) {
  return request<SearchRequestItem>("/search-requests", {
    method: "POST",
    body: JSON.stringify({ queryText, maxResults }),
  });
}

export function listProducts(searchRequestId: string) {
  return request<{ items: ProductDetail[]; total: number }>(`/search-requests/${searchRequestId}/products`);
}

export function getProduct(productId: string) {
  return request<ProductDetail>(`/products/${productId}`);
}

export function contactSupplier(productId: string, preferences: SupplierMessagePreferences) {
  return request(`/products/${productId}/contact-supplier`, {
    method: "POST",
    body: JSON.stringify(preferences),
  });
}

export function recordInboundMessage(productId: string, payload: InboundMessagePayload) {
  return request(`/products/${productId}/conversation-messages`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function requestAgentReply(
  productId: string,
  supplierContactId: string,
  replyToMessageId?: string,
  preferences?: SupplierMessagePreferences,
) {
  return request(`/products/${productId}/conversation-reply`, {
    method: "POST",
    body: JSON.stringify({ supplierContactId, replyToMessageId, ...(preferences ?? {}) }),
  });
}

export function syncGmailInbound(options: GmailSyncOptions = {}) {
  return request<{ messagesCreated: number; messagesSkipped: number; autoRepliesSent: number }>("/conversations/sync-gmail", {
    method: "POST",
    body: JSON.stringify(options),
  });
}
