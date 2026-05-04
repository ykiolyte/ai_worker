import { MessageSquareReply, Send } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { contactSupplier, getProduct, recordInboundMessage, requestAgentReply, syncGmailInbound } from "../api";
import { formatEmailTimestamp, formatNullable, formatPrice, statusClass, statusLabel } from "../components/format";
import type { ConversationMessage, ProductDetail, SupplierMessageLanguage, SupplierMessageStyle } from "../types";

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

export function ProductDetailsPage({ productId }: Props) {
  const [product, setProduct] = useState<ProductDetail>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [contactError, setContactError] = useState("");
  const [dialogueError, setDialogueError] = useState("");
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
      setProduct(await getProduct(productId));
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
      await requestAgentReply(productId, primaryContact.id, latestInbound?.id, preferences);
      await load();
    } catch (caught) {
      setDialogueError(caught instanceof Error ? caught.message : "Не удалось отправить ответ агентом");
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
      </header>
      <div className="product-detail-layout">
        <aside className="product-info-panel bubble-card">
          <p className="price-line">{formatPrice(product.price, product.currency)}</p>
          <p>{formatNullable(product.description, "Описание не указано")}</p>
          <a href={product.productUrl} target="_blank" rel="noreferrer">
            Источник товара
          </a>

          <section>
            <h3>Контакты поставщика</h3>
            {product.contacts.length === 0 && <p>Нет доступного контакта</p>}
            {product.contacts.map((contact) => (
              <p className="contact-pill" key={contact.id}>
                {contact.contactType}: {contact.contactValue}
              </p>
            ))}
          </section>

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
          <section className="timeline system-message" aria-label="Статус диалога">
            <span className={hasOutbound ? "done" : ""}>Отправлено</span>
            <span className={hasInbound ? "done" : ""}>Ответ получен</span>
            <span className={needsApproval ? "attention" : ""}>Нужно действие</span>
          </section>

          <section className="conversation-actions">
            <button className="action-button primary" type="button" disabled={!primaryContact || activeContact} onClick={submitAgentReply}>
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

