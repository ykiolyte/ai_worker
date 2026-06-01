import type { AdvancedSearchFields, ContractDraft, GmailSyncOptions, InboundMessagePayload, InternalAssistantMessage, ProductCatalogResponse, ProductDetail, SearchRequestItem, SupplierMessagePreferences } from "./types";

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL;
const sameOriginApiBaseUrl = `${window.location.origin}/api`;
const devApiBaseUrl = `${window.location.protocol}//${window.location.hostname}:8000/api`;
const browserApiBaseUrl = window.location.port === "5173" ? devApiBaseUrl : sameOriginApiBaseUrl;
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

export function createSearchRequest(queryText: string, maxResults: number): Promise<SearchRequestItem>;
export function createSearchRequest(queryText: string, maxResults: number, advanced: AdvancedSearchFields): Promise<SearchRequestItem>;
export function createSearchRequest(queryText: string, maxResults: number, advanced: AdvancedSearchFields = {}) {
  const body = Object.keys(advanced).length > 0
    ? JSON.stringify({ queryText, maxResults, ...advanced })
    : JSON.stringify({ queryText, maxResults });
  return request<SearchRequestItem>("/search-requests", {
    method: "POST",
    body,
  });
}

export function listProducts(searchRequestId: string) {
  return request<ProductCatalogResponse>(`/search-requests/${searchRequestId}/products`);
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

export function askProductAssistant(productId: string, message: string) {
  return request<{ reply: string; messages: InternalAssistantMessage[] }>(`/products/${productId}/assistant-chat`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export function listContractDrafts(productId: string) {
  return request<{ items: ContractDraft[] }>(`/products/${productId}/contracts`);
}

export function createContractDraft(productId: string) {
  return request<ContractDraft>(`/products/${productId}/contracts`, {
    method: "POST",
  });
}

export async function downloadContractDraft(contractId: string) {
  const response = await fetch(`${API_BASE_URL}/contracts/${contractId}/download`);
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: "Не удалось скачать договор" }));
    throw new Error(detail.detail ?? "Не удалось скачать договор");
  }
  return response.blob();
}

export async function downloadProductExport(productId: string) {
  const response = await fetch(`${API_BASE_URL}/products/${productId}/export.xlsx`);
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: "РќРµ СѓРґР°Р»РѕСЃСЊ СЃРєР°С‡Р°С‚СЊ Excel" }));
    throw new Error(detail.detail ?? "РќРµ СѓРґР°Р»РѕСЃСЊ СЃРєР°С‡Р°С‚СЊ Excel");
  }
  return response.blob();
}
