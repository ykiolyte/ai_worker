import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "frontend" / "src"


def read(path: str) -> str:
    return (SRC / path).read_text(encoding="utf-8")


class FrontendContractTest(unittest.TestCase):
    def test_search_requests_page_states_and_form(self):
        text = read("pages/SearchRequestsPage.tsx")
        for expected in ["loading", "queryText", "maxResults", "targetMarket", "quantity", "budget", "certifications", "supplierPreference", "min={1}", "max={50}"]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

    def test_sourcingai_like_search_experience_is_rendered(self):
        text = read("pages/SearchRequestsPage.tsx")
        for expected in [
            "sourcing-hero",
            "sourcing-prompt",
            "examples",
            "manufacturer_first",
            "SourcingAI",
            "ПК, вычислительные компьютеры, ноутбуки",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

    def test_search_requests_page_auto_refreshes_and_shows_progress(self):
        text = read("pages/SearchRequestsPage.tsx")
        for expected in ["setInterval", "hasActiveSearch", "progress-bar", "progressPercent"]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

    def test_search_requests_page_has_demo_dashboard_and_stage_badges(self):
        text = read("pages/SearchRequestsPage.tsx")
        helpers = read("components/format.ts")
        for expected in [
            "dashboard-grid",
            "Активные поиски",
            "Найдено товаров",
            "Ожидают ответа",
            "Получены ответы",
            "demo-mode-banner",
            "Демо-режим",
            "statusClass",
            "stageLabel",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text + helpers)

    def test_search_request_api_sends_max_results(self):
        api = read("api.ts")
        types = read("types.ts")

        self.assertIn("maxResults: number", types)
        self.assertIn("createSearchRequest(queryText: string, maxResults: number)", api)
        self.assertIn("JSON.stringify({ queryText, maxResults })", api)

    def test_request_catalog_has_duplicate_supplier_category(self):
        page = read("pages/RequestCatalogPage.tsx")
        api = read("api.ts")
        types = read("types.ts")
        for expected in [
            "duplicates",
            "ProductCatalogResponse",
            "duplicateReason",
            "isDuplicate",
            "Дубликаты",
            'catalogFilter === "duplicates"',
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, page + api + types)

    def test_supplier_message_preferences_are_typed_and_sent(self):
        api = read("api.ts")
        types = read("types.ts")

        self.assertIn("SupplierMessageLanguage", types)
        self.assertIn("SupplierMessageStyle", types)
        self.assertIn("SupplierMessagePreferences", types)
        self.assertIn("contactSupplier(productId: string, preferences", api)
        self.assertIn("requestAgentReply(", api)
        self.assertIn("preferences?: SupplierMessagePreferences", api)

    def test_request_catalog_states_and_pagination(self):
        text = read("pages/RequestCatalogPage.tsx")
        for expected in ["loading", "page", "items", "formatPrice", "missingFields", "clarifyingQuestions", "commonFilters", "productAttributes", "sourcingGuidance", "suppliersCount"]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

    def test_request_catalog_auto_refreshes(self):
        text = read("pages/RequestCatalogPage.tsx")
        for expected in ["setInterval", "listProducts(searchRequestId)", "progress-bar"]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

    def test_request_catalog_has_filters_contact_summaries_and_demo_badges(self):
        text = read("pages/RequestCatalogPage.tsx")
        types = read("types.ts")
        for expected in [
            "catalogFilter",
            "catalog-filters",
            "С контактом",
            "Без контакта",
            "Демо",
            "Email",
            "Telegram",
            "demo-badge",
            "contacts?: SupplierContact[]",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text + types)

    def test_request_catalog_splits_made_in_china_results_into_own_column(self):
        text = read("pages/RequestCatalogPage.tsx")
        types = read("types.ts")
        for expected in [
            "madeInChinaItems",
            "regularItems",
            "catalog-source-columns",
            "made-in-china-column",
            "Made-in-China",
            "sourcePlatform",
            "inquiryUrl",
            "moq",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text + types)

    def test_request_catalog_shows_supplier_comparison_rating(self):
        text = read("pages/RequestCatalogPage.tsx")
        types = read("types.ts")
        for expected in [
            "SupplierComparison",
            "supplierComparison",
            "overallRating",
            "priceRank",
            "priceDeltaPercent",
            "priceScore",
            "contactabilityScore",
            "responseScore",
            "dataCompletenessScore",
            "sourceTraceabilityScore",
            "supplier-rating",
            "comparison-metrics",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text + types)

    def test_request_catalog_shows_sourcing_fit_fields(self):
        text = read("pages/RequestCatalogPage.tsx")
        types = read("types.ts")
        for expected in [
            "priceRange",
            "fitScore",
            "fitSummary",
            "matchedRequirements",
            "missingRequirements",
            "supplierBadges",
            "Satisfies",
            "sourcing-guidance",
            "fit-score",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text + types)

    def test_request_catalog_renders_sourcing_filter_panel(self):
        text = read("pages/RequestCatalogPage.tsx")
        styles = read("styles.css")
        for expected in [
            "sourcing-filter-panel",
            "selectedCommonFilters",
            "selectedAttributeFilters",
            "priceMinimum",
            "priceMaximum",
            "matchesSourcingFilters",
            "matchesCommonFilter",
            "matchesAttributeFilter",
            "Clear filters",
            "Нет товаров по выбранным фильтрам",
            "selected-filter",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text + styles)

    def test_search_request_rows_link_to_catalog(self):
        text = read("pages/SearchRequestsPage.tsx")

        self.assertIn("/search-requests/${item.id}/products", text)

    def test_product_cards_link_to_product_details(self):
        text = read("pages/RequestCatalogPage.tsx")

        self.assertIn("/products/${product.id}", text)

    def test_demo_cards_do_not_link_to_unresolvable_demo_source(self):
        catalog = read("pages/RequestCatalogPage.tsx")
        detail = read("pages/ProductDetailsPage.tsx")

        self.assertIn('sourceDomain === "demo.local"', catalog + detail)
        self.assertIn("{!isDemo && (", catalog)
        self.assertIn("{!isDemo && (", detail)

    def test_product_details_contact_states(self):
        text = read("pages/ProductDetailsPage.tsx")
        for expected in [
            "contactSupplier",
            "conversationMessages",
            "inboundBody",
            "submitInboundMessage",
            "submitAgentReply",
            "recordInboundMessage",
            "requestAgentReply",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

    def test_product_details_message_preference_controls(self):
        text = read("pages/ProductDetailsPage.tsx")
        for expected in ["language", "style", "Русский", "English", "中文", "Кратко", "Формально", "Дружелюбно"]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

    def test_product_details_shows_continue_conversation_for_approval_needed_reply(self):
        text = read("pages/ProductDetailsPage.tsx")
        self.assertIn("requiresUserApproval", text)
        self.assertIn("Продолжить общение", text)

    def test_product_details_requests_automatic_ai_replies_for_gmail_sync(self):
        text = read("pages/ProductDetailsPage.tsx")
        api = read("api.ts")
        types = read("types.ts")

        for expected in [
            "requireAiReplyApproval",
            "syncGmailInbound({ requireAiReplyApproval: false })",
            "GmailSyncOptions",
            "requireAiReplyApproval?: boolean",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text + api + types)

        self.assertNotIn("Требовать подтверждение перед ответом ИИ", text)

    def test_product_details_has_demo_chat_layout_and_actions(self):
        text = read("pages/ProductDetailsPage.tsx")
        for expected in [
            "product-detail-layout",
            "product-info-panel",
            "conversation-panel",
            "timeline",
            "chat-message",
            "chat-message-outbound",
            "chat-message-inbound",
            "segmented-control",
            "setManualReplyVisible",
            "ErrorDetails",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertNotIn("previewMessage", text)
        self.assertNotIn("buildPreviewMessage", text)
        self.assertNotIn("message-preview", text)

    def test_product_detail_types_include_conversation_messages(self):
        text = read("types.ts")
        for expected in [
            "ConversationMessage",
            'direction: "outbound" | "inbound"',
            'status: "queued" | "sent" | "failed" | "received"',
            "conversationMessages: ConversationMessage[]",
            "InboundMessagePayload",
            "requiresUserApproval?: boolean",
            "approvalReason?: string",
            "providerTimestamp?: string",
            "durationSeconds?: number",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

    def test_supplier_dialogue_api_client_methods_exist(self):
        api = read("api.ts")
        for expected in ["recordInboundMessage", "requestAgentReply", "/conversation-messages", "/conversation-reply"]:
            with self.subTest(expected=expected):
                self.assertIn(expected, api)

    def test_product_details_can_download_supplier_excel_export(self):
        api = read("api.ts")
        page = read("pages/ProductDetailsPage.tsx")
        types = read("types.ts")
        for expected in [
            "downloadProductExport",
            "/export.xlsx",
            "saveProductExport",
            "РЎРѕС…СЂР°РЅРёС‚СЊ Excel",
            "contactQualityScore",
            "communicationScore",
            "isPreferred?: boolean",
            "qualityScore?: number",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, api + page + types)

    def test_product_details_has_contracts_tab_and_download_action(self):
        api = read("api.ts")
        page = read("pages/ProductDetailsPage.tsx")
        types = read("types.ts")
        for expected in [
            "ContractDraft",
            "contractDrafts",
            "listContractDrafts",
            "createContractDraft",
            "downloadContractDraft",
            "/contracts",
            "contracts-tab",
            "Договоры",
            "submitContractDraft",
            "saveContractDraft",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, api + page + types)

    def test_product_details_has_internal_ai_assistant_chat(self):
        api = read("api.ts")
        page = read("pages/ProductDetailsPage.tsx")
        types = read("types.ts")
        for expected in [
            "askProductAssistant",
            "/assistant-chat",
            "InternalAssistantMessage",
            "assistantMessages",
            "assistantOpen",
            "setAssistantOpen",
            "assistant-drawer",
            "loadedProduct.assistantMessages",
            "messages: InternalAssistantMessage[]",
            "assistantPrompts",
            "AI Assistant",
            "Внутренний чат не отправляет сообщения поставщику",
            "submitAssistantQuestion",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, api + page + types)

    def test_product_details_auto_syncs_gmail_before_loading(self):
        api = read("api.ts")
        page = read("pages/ProductDetailsPage.tsx")

        self.assertIn("syncGmailInbound", api)
        self.assertIn("/conversations/sync-gmail", api)
        self.assertIn("syncGmailInbound({ requireAiReplyApproval: false }).then", page)
        self.assertIn("getProduct(productId)", page)

    def test_product_details_gmail_sync_is_best_effort(self):
        page = read("pages/ProductDetailsPage.tsx")

        self.assertIn("await getProduct(productId)", page)
        self.assertIn("setInterval", page)

    def test_no_non_mvp_actions_are_rendered(self):
        combined = "\n".join(path.read_text(encoding="utf-8") for path in SRC.rglob("*.tsx"))
        forbidden = ["Купить", "Оформить заказ", "Оплатить", "Подтвердить поставку", "pipeline"]
        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, combined)

    def test_ui_uses_display_helpers_for_nullable_values(self):
        text = read("components/format.ts")
        self.assertIn("formatNullable", text)
        self.assertIn("value === null", text)
        self.assertIn("price === null", text)

    def test_api_base_url_supports_docker_host_browser_checks(self):
        text = read("api.ts")

        self.assertIn("host.docker.internal", text)
        self.assertIn("window.location.hostname", text)
        self.assertIn(":8000/api", text)

    def test_app_uses_messenger_shell_with_real_sidebar_and_theme_toggle(self):
        text = read("App.tsx")
        for expected in [
            "messenger-shell",
            "messenger-sidebar",
            "messenger-main",
            "listSearchRequests",
            "sidebar-items",
            "theme-toggle",
            "data-theme",
            "aria-label=\"Переключить тему\"",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

    def test_messenger_style_tokens_focus_motion_and_dark_theme_exist(self):
        text = read("styles.css")
        for expected in [
            "--app-bg",
            "--sidebar-bg",
            "--primary-accent",
            "--bubble-incoming",
            "--bubble-outgoing",
            "[data-theme=\"dark\"]",
            ":focus-visible",
            "@keyframes card-in",
            "@keyframes spin",
            "spinner",
            "transition",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

    def test_pages_use_chat_like_bubbles_and_action_buttons(self):
        combined = "\n".join(
            read(path)
            for path in [
                "pages/SearchRequestsPage.tsx",
                "pages/RequestCatalogPage.tsx",
                "pages/ProductDetailsPage.tsx",
            ]
        )
        for expected in [
            "chat-workspace",
            "system-message",
            "message-bubble",
            "attachment-card",
            "preview-media",
            "action-button",
            "bubble-card",
            "aria-label",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, combined)

    def test_supplier_messages_have_rounded_bubble_tails_and_text_wrapping(self):
        page = read("pages/ProductDetailsPage.tsx")
        styles = read("styles.css")
        for expected in [
            "message-subject",
            "message-text",
            "message-time",
            "providerTimestamp",
            "formatEmailTimestamp",
            "chat-message::after",
            "border-radius: 16px",
            "width: fit-content",
            "overflow-wrap: anywhere",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, page + styles)

    def test_frontend_displays_actual_search_duration(self):
        combined = read("pages/SearchRequestsPage.tsx") + read("pages/RequestCatalogPage.tsx") + read("components/format.ts")
        for expected in ["durationSeconds", "formatDuration", "Поиск занял"]:
            with self.subTest(expected=expected):
                self.assertIn(expected, combined)


if __name__ == "__main__":
    unittest.main()
