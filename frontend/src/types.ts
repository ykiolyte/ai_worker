export type SearchRequestStatus = "queued" | "running" | "completed" | "failed" | "cancelled";
export type ContactAttemptStatus = "queued" | "running" | "sent" | "responded" | "failed" | "cancelled";
export type SupplierMessageLanguage = "ru" | "en" | "zh";
export type SupplierMessageStyle = "concise" | "formal" | "friendly";

export interface SupplierMessagePreferences {
  language: SupplierMessageLanguage;
  style: SupplierMessageStyle;
}

export interface GmailSyncOptions {
  requireAiReplyApproval?: boolean;
}

export interface SearchRequestItem {
  id: string;
  queryText: string;
  maxResults: number;
  status: SearchRequestStatus;
  createdAt: string;
  updatedAt?: string | null;
  startedAt?: string | null;
  completedAt?: string | null;
  durationSeconds?: number | null;
  productsCount: number;
  awaitingRepliesCount?: number;
  receivedRepliesCount?: number;
  errorMessage?: string | null;
}

export interface ProductCard {
  id: string;
  searchRequestId: string;
  title: string;
  description?: string | null;
  price?: string | null;
  currency?: string | null;
  productUrl: string;
  supplierName?: string | null;
  sourceDomain?: string | null;
  images: string[];
  attributes: Record<string, string>;
  contacts?: SupplierContact[];
}

export interface SupplierContact {
  id: string;
  contactType: "email" | "telegram";
  contactValue: string;
  isPrimary: boolean;
}

export interface ContactAttempt {
  id: string;
  channel: "email" | "telegram";
  status: ContactAttemptStatus;
  messageText: string;
  errorMessage?: string | null;
}

export interface ConversationMessage {
  id: string;
  contactAttemptId: string;
  supplierContactId: string;
  direction: "outbound" | "inbound";
  channel: "email" | "telegram";
  status: "queued" | "sent" | "failed" | "received";
  subject?: string | null;
  body: string;
  fromAddress?: string | null;
  toAddress?: string | null;
  externalMessageId?: string | null;
  providerTimestamp?: string | null;
  errorMessage?: string | null;
  requiresUserApproval?: boolean;
  approvalReason?: string | null;
  createdAt: string;
  sentAt?: string | null;
}

export interface ProductDetail extends ProductCard {
  contacts: SupplierContact[];
  contactAttempts: ContactAttempt[];
  conversationMessages: ConversationMessage[];
}

export interface InboundMessagePayload {
  supplierContactId: string;
  contactAttemptId: string;
  channel: "email" | "telegram";
  subject?: string | null;
  body: string;
  fromAddress?: string | null;
  toAddress?: string | null;
  externalMessageId?: string | null;
  providerTimestamp?: string | null;
}
