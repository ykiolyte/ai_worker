export function formatNullable(value: string | number | null | undefined, fallback = "Не указано") {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }
  return String(value);
}

export function formatPrice(price: string | null | undefined, currency: string | null | undefined) {
  if (price === undefined || price === null || price === "") {
    return "Цена не найдена";
  }
  return currency ? `${price} ${currency}` : price;
}

export function formatDuration(seconds: number | null | undefined) {
  if (seconds === undefined || seconds === null) {
    return "РµС‰Рµ РЅРµ Р·Р°РІРµСЂС€РµРЅ";
  }
  const normalized = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(normalized / 60);
  const remainder = normalized % 60;
  if (minutes === 0) {
    return `${remainder} СЃРµРє.`;
  }
  return `${minutes} РјРёРЅ. ${remainder} СЃРµРє.`;
}

export function formatEmailTimestamp(value: string | null | undefined) {
  if (!value) {
    return "Р’СЂРµРјСЏ Gmail РЅРµРґРѕСЃС‚СѓРїРЅРѕ";
  }
  return new Date(value).toLocaleString();
}

export function statusLabel(status: string) {
  const labels: Record<string, string> = {
    queued: "В очереди",
    running: "Выполняется",
    completed: "Завершён",
    failed: "Ошибка",
    cancelled: "Отменён",
    sent: "Отправлено",
    responded: "Получен ответ",
    received: "Получено",
  };
  return labels[status] ?? status;
}

export function statusClass(status: string) {
  return `status-badge status-${status}`;
}

export function stageLabel(status: string, productsCount = 0) {
  if (status === "queued") {
    return "Агент готовит поиск";
  }
  if (status === "running" && productsCount === 0) {
    return "Агент ищет поставщиков";
  }
  if (status === "running") {
    return "Проверяет карточки";
  }
  if (status === "completed") {
    return "Сохраняет результаты";
  }
  if (status === "failed") {
    return "Нужна проверка ошибки";
  }
  return statusLabel(status);
}

export function progressPercent(status: string, createdAt: string, completedAt?: string | null) {
  if (status === "completed") {
    return 100;
  }
  if (status === "failed" || status === "cancelled") {
    return 100;
  }
  const started = new Date(createdAt).getTime();
  const finished = completedAt ? new Date(completedAt).getTime() : Date.now();
  const elapsedSeconds = Math.max(0, (finished - started) / 1000);
  const estimateSeconds = 90;
  const base = status === "queued" ? 8 : 20;
  return Math.min(95, Math.round(base + (elapsedSeconds / estimateSeconds) * 75));
}

export function remainingHint(status: string, createdAt: string) {
  if (status !== "queued" && status !== "running") {
    return "";
  }
  const elapsedSeconds = Math.max(0, (Date.now() - new Date(createdAt).getTime()) / 1000);
  const remaining = Math.max(10, Math.round(90 - elapsedSeconds));
  return `примерно ${Math.ceil(remaining / 10) * 10} сек.`;
}
