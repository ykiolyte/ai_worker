import { Bot, Download, FileText, MessageSquareReply, Send, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { askProductAssistant, contactSupplier, createContractDraft, downloadContractDraft, downloadProductExport, getProduct, listContractDrafts, recordInboundMessage, requestAgentReply, syncGmailInbound } from "../api";
import { formatEmailTimestamp, formatNullable, formatPrice, formatPriceDelta, formatPriceRank, ratingLabel, statusClass, statusLabel } from "../components/format";
import type { ContractDraft, ConversationMessage, InternalAssistantMessage, ProductDetail, SupplierMessageLanguage, SupplierMessageStyle } from "../types";

interface Props {
  productId: string;
}

const languageOptions: Array<[SupplierMessageLanguage, string]> = [
  ["ru", "Русский"],
  ["en", "English"],
  ["zh", "中文"],
];

const styleOptions: Array<[SupplierMessageStyle, string]> = [
  ["concise", "Кратко"],
  ["formal", "Формально"],
  ["friendly", "Дружелюбно"],
];

const assistantPrompts = [
  "Что спросить у поставщика дальше?",
  "Оцени риски по этому поставщику",
  "Сравни условия и выдели слабые места",
  "Сформулируй короткий черновик письма, но не отправляй",
];

export function ProductDetailsPage({ productId }: Props) {
  const [product, setProduct] = useState<ProductDetail>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [contactError, setContactError] = useState("");
  const [dialogueError, setDialogueError] = useState("");
  const [exportError, setExportError] = useState("");
  const [assistantError, setAssistantError] = useState("");
  const [assistantInput, setAssistantInput] = useState("");
  const [assistantBusy, setAssistantBusy] = useState(false);
  const [assistantMessages, setAssistantMessages] = useState<InternalAssistantMessage[]>([]);
  const [contractDrafts, setContractDrafts] = useState<ContractDraft[]>([]);
  const [contractError, setContractError] = useState("");
  const [contractBusy, setContractBusy] = useState(false);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [inboundBody, setInboundBody] = useState("");
  const [inboundSubject, setInboundSubject] = useState("");
  const [manualReplyVisible, setManualReplyVisible] = useState(false);
  const [language, setLanguage] = useState<SupplierMessageLanguage>("ru");
  const [style, setStyle] = useState<SupplierMessageStyle>("formal");

  async function load(silent = false) {
    if (!silent) {
      setLoading(true);
    }
    setError("");
    try {
      const loadedProduct = await getProduct(productId);
      setProduct(loadedProduct);
      setAssistantMessages(loadedProduct.assistantMessages ?? []);
      const contracts = await listContractDrafts(productId);
      setContractDrafts(contracts.items);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось загрузить товар");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [productId]);

  useEffect(() => {
    syncGmailInbound({ requireAiReplyApproval: false }).then((result) => {
      if (result.messagesCreated > 0 || result.autoRepliesSent > 0) {
        void load(true);
      }
    }).catch(() => undefined);
  }, [productId]);

  const activeContact = useMemo(
    () => product?.contactAttempts.some((attempt) => attempt.status === "queued" || attempt.status === "running") ?? false,
    [product],
  );
  const hasContact = (product?.contacts.length ?? 0) > 0;
  const primaryContact = product?.contacts[0];
  const preferences = { language, style };

  useEffect(() => {
    if (!product || !activeContact) {
      return;
    }
    const timer = window.setInterval(() => {
      void load(true);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [product?.id, activeContact]);

  async function submitContact() {
    setContactError("");
    try {
      await contactSupplier(productId, preferences);
      await load();
    } catch (caught) {
      setContactError(caught instanceof Error ? caught.message : "Не удалось начать общение");
    }
  }

  async function submitInboundMessage() {
    if (!product || !primaryContact || product.contactAttempts.length === 0) {
      return;
    }
    setDialogueError("");
    try {
      await recordInboundMessage(productId, {
        supplierContactId: primaryContact.id,
        contactAttemptId: product.contactAttempts[product.contactAttempts.length - 1].id,
        channel: primaryContact.contactType,
        subject: inboundSubject || null,
        body: inboundBody,
        fromAddress: primaryContact.contactValue,
      });
      setInboundBody("");
      setInboundSubject("");
      await load();
    } catch (caught) {
      setDialogueError(caught instanceof Error ? caught.message : "Не удалось записать ответ поставщика");
    }
  }

  async function submitAgentReply() {
    if (!product || !primaryContact) {
      return;
    }
    setDialogueError("");
    try {
      const latestInbound = [...conversationMessages].reverse().find((message) => message.direction === "inbound");
      const replyContactId = latestInbound?.supplierContactId ?? primaryContact.id;
      await requestAgentReply(productId, replyContactId, latestInbound?.id, preferences);
      await load();
    } catch (caught) {
      setDialogueError(caught instanceof Error ? caught.message : "Не удалось отправить ответ агентом");
    }
  }

  async function saveProductExport() {
    setExportError("");
    try {
      const blob = await downloadProductExport(productId);
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `product-supplier-${productId}.xls`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
    } catch (caught) {
      setExportError(caught instanceof Error ? caught.message : "РќРµ СѓРґР°Р»РѕСЃСЊ СЃРѕС…СЂР°РЅРёС‚СЊ Excel");
    }
  }

  async function submitContractDraft() {
    setContractError("");
    setContractBusy(true);
    try {
      await createContractDraft(productId);
      const contracts = await listContractDrafts(productId);
      setContractDrafts(contracts.items);
    } catch (caught) {
      setContractError(caught instanceof Error ? caught.message : "Не удалось подготовить договор");
    } finally {
      setContractBusy(false);
    }
  }

  async function saveContractDraft(draft: ContractDraft) {
    setContractError("");
    try {
      const blob = await downloadContractDraft(draft.id);
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = draft.fileName || `contract-draft-${draft.id}.txt`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
    } catch (caught) {
      setContractError(caught instanceof Error ? caught.message : "Не удалось скачать договор");
    }
  }

  async function submitAssistantQuestion(message = assistantInput) {
    const question = message.trim();
    if (!question || assistantBusy) {
      return;
    }
    setAssistantError("");
    setAssistantBusy(true);
    setAssistantMessages((current) => [...current, { id: `${Date.now()}-user`, role: "user", body: question }]);
    setAssistantInput("");
    setAssistantOpen(true);
    try {
      const result = await askProductAssistant(productId, question);
      setAssistantMessages(result.messages);
      setProduct((current) => current ? { ...current, assistantMessages: result.messages } : current);
    } catch (caught) {
      setAssistantError(caught instanceof Error ? caught.message : "Не удалось получить ответ AI Assistant");
    } finally {
      setAssistantBusy(false);
    }
  }

  if (loading) {
    return <p role="status">Загрузка товара</p>;
  }
  if (error || product === undefined) {
    return <ErrorDetails title="Не удалось загрузить товар" details={error} />;
  }

  const disabledReason = !hasContact ? "Нет доступного контакта" : activeContact ? "Общение уже запускается" : "";
  const conversationMessages = product.conversationMessages ?? [];
  const isDemo = product.attributes.demo === "true" || product.sourceDomain === "demo.local";
  const hasInbound = conversationMessages.some((message) => message.direction === "inbound");
  const hasOutbound = conversationMessages.some((message) => message.direction === "outbound");
  const needsApproval = conversationMessages.some((message) => message.requiresUserApproval);

  return (
    <section className="workspace chat-workspace">
      <header className="chat-header">
        <div>
          <h2>{product.title}</h2>
          <p>Карточка товара и история связи с поставщиком.</p>
        </div>
        <button className="action-button secondary" type="button" onClick={() => setAssistantOpen(true)}>
          <Bot aria-hidden="true" />
          AI Assistant
        </button>
      </header>
      <div className="product-detail-layout">
        <aside className="product-info-panel bubble-card">
          <p className="price-line">{formatPrice(product.price, product.currency)}</p>
          {product.priceRange && <p className="price-line">{product.priceRange}</p>}
          {product.moq && <p>MOQ: {product.moq}</p>}
          <p>{formatNullable(product.description, "Описание не указано")}</p>
          {(product.supplierBadges ?? []).length > 0 && (
            <div className="chip-row">{(product.supplierBadges ?? []).map((badge) => <span className="source-badge" key={badge}>{badge}</span>)}</div>
          )}
          {product.fitScore && <p className="fit-score">Fit {Math.round(Number(product.fitScore) * 100)}%</p>}
          {product.fitSummary && <p>{product.fitSummary}</p>}
          {(product.matchedRequirements ?? []).length > 0 && (
            <section>
              <h3>Matched requirements</h3>
              {(product.matchedRequirements ?? []).map((item) => (
                <p key={`${item.requirement}-${item.evidence}`}><strong>{item.requirement}</strong>: {item.evidence}</p>
              ))}
            </section>
          )}
          {(product.missingRequirements ?? []).length > 0 && (
            <section>
              <h3>Missing requirements</h3>
              <p>{(product.missingRequirements ?? []).join(", ")}</p>
            </section>
          )}
          {product.supplierComparison && (
            <section className="supplier-score-panel">
              <h3>Supplier rating</h3>
              <strong className={`supplier-rating rating-${product.supplierComparison.ratingLabel}`}>
                {product.supplierComparison.overallRating}/100
              </strong>
              <p>{ratingLabel(product.supplierComparison.ratingLabel)}</p>
              <div className="comparison-metrics">
                <span>{formatPriceRank(product.supplierComparison.priceRank, product.supplierComparison.comparedProductsCount)}</span>
                <span>{formatPriceDelta(product.supplierComparison.priceDeltaPercent)}</span>
                <span>Price {product.supplierComparison.metrics.priceScore}</span>
                <span>Contact {product.supplierComparison.metrics.contactabilityScore}</span>
                <span>Contact quality {product.supplierComparison.metrics.contactQualityScore}</span>
                <span>Response {product.supplierComparison.metrics.responseScore}</span>
                <span>Communication {product.supplierComparison.metrics.communicationScore}</span>
                <span>Data {product.supplierComparison.metrics.dataCompletenessScore}</span>
                <span>Source {product.supplierComparison.metrics.sourceTraceabilityScore}</span>
              </div>
            </section>
          )}
          {!isDemo && (
            <a href={product.productUrl} target="_blank" rel="noopener noreferrer">
            Источник товара
            </a>
          )}

          <section>
            <h3>Контакты поставщика</h3>
            {product.contacts.length === 0 && <p>Нет доступного контакта</p>}
            {product.contacts.map((contact) => (
              <p className="contact-pill" key={contact.id}>
                {contact.contactType}: {contact.contactValue}
                {contact.isPreferred ? " | preferred" : ""}
                {contact.qualityScore !== undefined ? ` | ${contact.qualityScore}/100` : ""}
              </p>
            ))}
          </section>

          <button className="action-button secondary" type="button" onClick={saveProductExport}>
            <Download aria-hidden="true" />
            РЎРѕС…СЂР°РЅРёС‚СЊ Excel
          </button>
          {exportError && <ErrorDetails title="РќРµ СѓРґР°Р»РѕСЃСЊ СЃРѕС…СЂР°РЅРёС‚СЊ Excel" details={exportError} />}

          <section>
            <h3>Настройки сообщения</h3>
            <SegmentedControl
              label="Язык"
              options={languageOptions}
              value={language}
              onChange={setLanguage}
            />
            <SegmentedControl
              label="Стиль"
              options={styleOptions}
              value={style}
              onChange={setStyle}
            />
          </section>


          <button className="action-button primary" type="button" disabled={!hasContact || activeContact} onClick={submitContact}>
            <Send aria-hidden="true" />
            Начать общение
          </button>
          {disabledReason && <p className="muted">{disabledReason}</p>}
          {contactError && <ErrorDetails title="Не удалось начать общение" details={contactError} />}
        </aside>

        <main className="conversation-panel">
          <section className="contracts-tab bubble-card">
            <div className="contracts-header">
              <h3><FileText aria-hidden="true" /> Договоры</h3>
              <button className="action-button secondary" type="button" disabled={contractBusy || !hasContact} onClick={submitContractDraft}>
                <FileText aria-hidden="true" />
                Составить договор
              </button>
            </div>
            {contractDrafts.length === 0 && <p className="system-message">Черновиков договоров пока нет.</p>}
            {contractDrafts.map((draft) => (
              <article className="attachment-card" key={draft.id}>
                <div className="message-meta">
                  <span>{draft.title}</span>
                  <span className={statusClass(draft.status)}>{draft.status}</span>
                </div>
                {draft.missingFields.length > 0 && <p>Не хватает: {draft.missingFields.join(", ")}</p>}
                {draft.errorMessage && <ErrorDetails title="Ошибка договора" details={draft.errorMessage} />}
                <button className="action-button primary" type="button" disabled={draft.status !== "ready"} onClick={() => void saveContractDraft(draft)}>
                  <Download aria-hidden="true" />
                  Скачать
                </button>
              </article>
            ))}
            {contractError && <ErrorDetails title="Не удалось обработать договор" details={contractError} />}
          </section>
          <section className="timeline system-message" aria-label="Статус диалога">
            <span className={hasOutbound ? "done" : ""}>Отправлено</span>
            <span className={hasInbound ? "done" : ""}>Ответ получен</span>
            <span className={needsApproval ? "attention" : ""}>Нужно действие</span>
          </section>

          <section className="conversation-actions">
            <button className="action-button primary" type="button" disabled={!primaryContact || !hasInbound || activeContact} onClick={submitAgentReply}>
              <Send aria-hidden="true" />
              Ответить агентом
            </button>
            <button className="action-button secondary" type="button" onClick={() => setManualReplyVisible((current) => !current)}>
              <MessageSquareReply aria-hidden="true" />
              Ответить вручную
            </button>
          </section>

          {(manualReplyVisible || inboundBody.length > 0) && (
            <section className="manual-reply-panel bubble-card">
              <h3>Ответ поставщика</h3>
              <label>
                <span>Тема ответа поставщика</span>
                <input
                  aria-label="Тема ответа поставщика"
                  value={inboundSubject}
                  onChange={(event) => setInboundSubject(event.target.value)}
                  placeholder="Тема письма"
                />
              </label>
              <label>
                <span>Ответ поставщика</span>
                <textarea
                  aria-label="Ответ поставщика"
                  value={inboundBody}
                  onChange={(event) => setInboundBody(event.target.value)}
                  placeholder="Текст ответа поставщика"
                  rows={4}
                />
              </label>
              <button
                className="action-button primary"
                type="button"
                disabled={!primaryContact || product.contactAttempts.length === 0 || inboundBody.trim().length === 0}
                onClick={submitInboundMessage}
              >
                <MessageSquareReply aria-hidden="true" />
                Записать ответ
              </button>
            </section>
          )}
          {dialogueError && <ErrorDetails title="Не удалось обновить переписку" details={dialogueError} />}

          <section>
            <h3>Переписка с поставщиком</h3>
            <div className="chat-thread">
              {conversationMessages.length === 0 && <p className="system-message">Переписка пока пустая</p>}
              {conversationMessages.map((message) => (
                <ConversationMessageItem key={message.id} message={message} onContinue={submitAgentReply} />
              ))}
            </div>
          </section>
        </main>
      </div>
      {assistantOpen && (
        <aside className="assistant-drawer bubble-card" aria-label="Internal AI Assistant">
          <div className="assistant-drawer-header">
            <h3><Bot aria-hidden="true" /> AI Assistant</h3>
            <button className="icon-button" type="button" aria-label="Закрыть AI Assistant" onClick={() => setAssistantOpen(false)}>
              <X aria-hidden="true" />
            </button>
          </div>
          <div className="assistant-quick-actions">
            {assistantPrompts.map((prompt) => (
              <button className="action-button secondary" type="button" key={prompt} disabled={assistantBusy} onClick={() => void submitAssistantQuestion(prompt)}>
                {prompt}
              </button>
            ))}
          </div>
          <div className="assistant-thread">
            {assistantMessages.length === 0 && <p className="system-message">Внутренний чат не отправляет сообщения поставщику.</p>}
            {assistantMessages.map((message) => (
              <article className={`assistant-message ${message.role}`} key={message.id}>
                <strong>{message.role === "user" ? "Вы" : "AI Assistant"}</strong>
                <p>{message.body}</p>
              </article>
            ))}
          </div>
          <form
            className="assistant-input"
            onSubmit={(event) => {
              event.preventDefault();
              void submitAssistantQuestion();
            }}
          >
            <input
              aria-label="Вопрос внутреннему AI Assistant"
              value={assistantInput}
              onChange={(event) => setAssistantInput(event.target.value)}
              placeholder="Спросите о рисках, условиях или следующем шаге"
            />
            <button className="action-button primary" type="submit" disabled={assistantBusy || assistantInput.trim().length === 0}>
              <Bot aria-hidden="true" />
              Спросить
            </button>
          </form>
          {assistantError && <ErrorDetails title="Ошибка AI Assistant" details={assistantError} />}
        </aside>
      )}
    </section>
  );
}

function SegmentedControl<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: Array<[T, string]>;
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div className="preference-grid">
      <span>{label}</span>
      <div className="segmented-control" role="group" aria-label={label}>
        {options.map(([optionValue, optionLabel]) => (
          <button
            key={optionValue}
            type="button"
            className={value === optionValue ? "active" : ""}
            onClick={() => onChange(optionValue)}
          >
            {optionLabel}
          </button>
        ))}
      </div>
    </div>
  );
}

function ConversationMessageItem({ message, onContinue }: { message: ConversationMessage; onContinue: () => void }) {
  const directionLabel = message.direction === "outbound" ? "Исходящее" : "Входящее";
  const address = message.direction === "outbound" ? message.toAddress : message.fromAddress;
  const directionClass = message.direction === "outbound" ? "chat-message-outbound" : "chat-message-inbound";

  return (
    <article className={`conversation-message message-bubble chat-message ${directionClass}`}>
      <div className="message-meta">
        <span>{directionLabel}</span>
        <span>{message.channel}</span>
        <span className={statusClass(message.status)}>{statusLabel(message.status)}</span>
      </div>
      {message.subject && <h4 className="message-subject">{message.subject}</h4>}
      <p className="message-text">{message.body}</p>
      <p className="message-address">{formatNullable(address, "Адрес не указан")}</p>
      <time className="message-time" dateTime={message.providerTimestamp ?? undefined}>
        Gmail: {formatEmailTimestamp(message.providerTimestamp)}
      </time>
      {message.requiresUserApproval && (
        <div className="approval-panel">
          <p>{formatNullable(message.approvalReason, "Требуется подтверждение пользователя")}</p>
          <button className="action-button primary" type="button" onClick={onContinue}>
            <MessageSquareReply aria-hidden="true" />
            Продолжить общение
          </button>
        </div>
      )}
      {message.errorMessage && <ErrorDetails title="Ошибка сообщения" details={message.errorMessage} />}
    </article>
  );
}

function ErrorDetails({ title, details }: { title: string; details: string }) {
  return (
    <div className="error-summary" role="alert">
      <strong>{title}</strong>
      {details && (
        <details>
          <summary>Подробнее</summary>
          <code>{details}</code>
        </details>
      )}
    </div>
  );
}

