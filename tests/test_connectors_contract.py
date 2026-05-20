import unittest
import json
from datetime import timezone

from backend.app.agent import ConnectorResult
from backend.app.config import Settings
from backend.app.connectors import (
    AiInternetProductSearchConnector,
    BrowserSecurityError,
    DuckDuckGoHtmlWebSearchConnector,
    EXTRACT_PRODUCT_CODE,
    GmailImapInboundConnector,
    InboundEmailMessage,
    MadeInChinaSearchConnector,
    McpProtocolError,
    McpHttpClient,
    MultiEngineWebSearchConnector,
    PlaywrightMcpBrowserConnector,
    SearxngWebSearchConnector,
    SmtpEmailConnector,
    TelegramBotConnector,
    WebSearchResult,
    _split_args,
    build_web_search_connector,
    build_tool_registry,
    parse_mcp_tool_json,
)


class FakeMcpClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.initialized = False
        self.closed = False

    def initialize(self):
        self.initialized = True

    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        if name != "browser_evaluate":
            return {"content": [{"type": "text", "text": "{}"}]}
        if not self.responses:
            return {"content": [{"type": "text", "text": "{}"}]}
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def close(self):
        self.closed = True


class UrlAwareMcpClient:
    def __init__(self, page_payloads):
        self.page_payloads = dict(page_payloads)
        self.calls = []
        self.current_url = ""
        self.closed = False

    def initialize(self):
        pass

    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        if name == "browser_navigate":
            self.current_url = arguments["url"]
            return {"content": [{"type": "text", "text": "{}"}]}
        if name == "browser_evaluate":
            payload = self.page_payloads.get(self.current_url, {})
            return {"content": [{"type": "text", "text": json.dumps(payload)}]}
        return {"content": [{"type": "text", "text": "{}"}]}

    def close(self):
        self.closed = True


class FakeSmtp:
    instances = []

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.logged_in = None
        self.messages = []
        self.closed = False
        FakeSmtp.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.closed = True

    def starttls(self, context=None):
        self.started_tls = True

    def login(self, user, password):
        self.logged_in = (user, password)

    def send_message(self, message):
        self.messages.append(message)
        return {}


class FailingSmtp(FakeSmtp):
    def send_message(self, message):
        raise RuntimeError("SMTP rejected password super-secret")


class FakeImap:
    instances = []

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.logged_in = None
        self.selected = None
        self.closed = False
        self.logged_out = False
        FakeImap.instances.append(self)

    def login(self, user, password):
        self.logged_in = (user, password)

    def select(self, mailbox):
        self.selected = mailbox
        return "OK", [b"1"]

    def search(self, charset, criteria):
        return "OK", [b"1"]

    def fetch(self, message_id, query):
        msg_id = message_id.decode("ascii") if isinstance(message_id, bytes) else str(message_id)
        raw = (
            "From: Supplier <supplier@example.test>\r\n"
            "To: agent@example.test\r\n"
            "Subject: Re: Product request\r\n"
            f"Message-ID: <gmail-inbound-{msg_id}@example.test>\r\n"
            "Date: Sat, 02 May 2026 18:55:53 +0300\r\n"
            "In-Reply-To: <gmail-outbound-1@example.test>\r\n"
            "References: <gmail-outbound-1@example.test>\r\n"
            "\r\n"
            f"We have stock. MOQ is 10 units. Message {msg_id}."
        ).encode("utf-8")
        return "OK", [(b"1 (RFC822 {100}", raw)]

    def store(self, message_id, command, flags):
        return "OK", [b"1"]

    def close(self):
        self.closed = True

    def logout(self):
        self.logged_out = True


class FailingImap(FakeImap):
    def login(self, user, password):
        raise RuntimeError(f"bad password {password}")


class ManyMessageImap(FakeImap):
    def search(self, charset, criteria):
        return "OK", [b"1 2 3 4 5"]


class QuotedReplyImap(FakeImap):
    def fetch(self, message_id, query):
        raw = (
            "From: Supplier <supplier@example.test>\r\n"
            "To: agent@example.test\r\n"
            "Subject: Re: Product request\r\n"
            "Message-ID: <gmail-inbound-clean@example.test>\r\n"
            "Content-Type: text/plain; charset=utf-8\r\n"
            "\r\n"
            "Здравствуйте, какую компанию вы представляете? вс, 3 мая 2026 г. в 00:20, <bbimba385@gmail.com>:\r\n"
            "> Здравствуйте.\r\n"
            "> Интересует товар: Демо-карточка для презентации\r\n"
            "> Ссылка на товар: https://demo.local/product\r\n"
        ).encode("utf-8")
        return "OK", [(b"1 (RFC822 {100}", raw)]


class ToolErrorMcpClient:
    def __init__(self):
        self.closed = False

    def initialize(self):
        pass

    def call_tool(self, name, arguments):
        return {
            "content": [
                {
                    "type": "text",
                    "text": "### Error\nError: Chromium distribution 'chrome' is not found",
                }
            ],
            "isError": True,
        }

    def close(self):
        self.closed = True


class ProductNavigateFailClient(FakeMcpClient):
    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        if name == "browser_navigate":
            raise McpProtocolError("page snapshot failed")
        return {"content": [{"type": "text", "text": "{}"}]}


class FakeModelProvider:
    name = "fake-ai"

    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def complete_json(self, prompt):
        self.prompts.append(prompt)
        if not self.responses:
            return {}
        return self.responses.pop(0)

    def complete(self, prompt, tools=None):
        return json.dumps(self.complete_json(prompt))


class FailingModelProvider:
    name = "failing-ai"

    def __init__(self):
        self.prompts = []

    def complete_json(self, prompt):
        self.prompts.append(prompt)
        raise ValueError("invalid model JSON")


class FakeWebSearch:
    def __init__(self, results):
        self.results = list(results)
        self.queries = []

    def search(self, query):
        self.queries.append(query)
        return list(self.results)


class FailingWebSearch:
    def __init__(self, message="search engine unavailable"):
        self.message = message
        self.queries = []

    def search(self, query):
        self.queries.append(query)
        raise RuntimeError(self.message)


def json_response(request_id, result):
    return json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result})


def make_settings(**overrides):
    values = dict(
        app_env="test",
        webui_base_url="http://localhost:5173",
        api_base_url="http://localhost:8000/api",
        database_url="postgresql+psycopg://user:pass@localhost/db",
        redis_url="redis://localhost:6379/0",
        model_provider="fake",
        model_name="fake-model",
        ollama_base_url="http://ollama:11434",
        ollama_timeout_seconds=60,
        browser_provider="playwright_mcp",
        browser_mcp_service_name="browser-mcp",
        browser_mcp_url="http://browser-mcp:8931/mcp",
        browser_mcp_command="npx",
        browser_mcp_args="@playwright/mcp@latest --headless --isolated",
        browser_allowed_domains="supplier.test,localhost",
        browser_research_mode="site",
        browser_allow_public_internet=False,
        internet_search_url_template="https://duckduckgo.com/html/?q={query}",
        internet_search_result_limit=5,
        web_search_provider="searxng",
        web_search_engines="",
        web_search_url="http://searxng:8080/search",
        web_search_result_limit=20,
        ai_search_query_count=3,
        ai_search_candidate_limit=5,
        email_connector_provider="smtp",
        email_smtp_host="smtp.test",
        email_smtp_port=2525,
        email_smtp_user="user",
        email_smtp_password="super-secret",
        email_from="agent@example.test",
        email_use_tls=True,
        email_use_ssl=False,
        email_timeout_seconds=10,
        email_inbound_provider="gmail_imap",
        email_imap_host="imap.gmail.com",
        email_imap_port=993,
        email_imap_user="agent@example.test",
        email_imap_password="gmail-app-password",
        email_imap_mailbox="INBOX",
        email_inbound_sync_limit=20,
        telegram_connector_provider="telegram_bot",
        telegram_bot_token="telegram-secret",
        telegram_chat_id="@supplier_e2e_test",
        telegram_timeout_seconds=10,
        test_supplier_site_url="https://supplier.test",
        test_supplier_email="supplier@example.test",
        test_supplier_telegram="@supplier_e2e_test",
    )
    values.update(overrides)
    return Settings(**values)


class ConnectorContractTest(unittest.TestCase):
    def test_made_in_china_connector_extracts_search_results(self):
        calls = []

        def http_get(url, timeout):
            calls.append((url, timeout))
            return 200, """
            <html><body>
              <div class="product">
                <h2 class="product-name">
                  <a title="Industrial CNC Controller IC-200" href="//cnc.en.made-in-china.com/product/ic200.html">Industrial CNC Controller IC-200</a>
                </h2>
                <div class="price-new"><strong class="price">US$ <span>120</span>-<span>150</span></strong></div>
                <div class="moq-new"><span class="attribute">10 Pieces</span></div>
                <a class="compnay-name" title="Shenzhen CNC Factory" href="//cnc.en.made-in-china.com">Shenzhen CNC Factory</a>
                <div class="address-info">Guangdong, China</div>
                <div class="business-type-info">Manufacturer/Factory</div>
                <img data-original="//image.made-in-china.com/ic200.jpg" />
              </div>
              <div class="product">
                <h2 class="product-name">
                  <a title="Rack Workstation RW-500" href="https://rack.en.made-in-china.com/product/rw500.html">Rack Workstation RW-500</a>
                </h2>
                <div class="price-new"><strong class="price">US$ 840</strong></div>
                <div class="moq-new">1 Piece (MOQ)</div>
                <a class="compnay-name" title="Rack Supplier" href="https://rack.en.made-in-china.com">Rack Supplier</a>
              </div>
            </body></html>
            """

        connector = MadeInChinaSearchConnector(http_get=http_get, max_results=1, timeout_seconds=7)

        result = connector.research("industrial cnc controller", max_results=5)

        self.assertTrue(result.success, result.error_message)
        self.assertIn("industrial_cnc_controller", calls[0][0])
        self.assertEqual(7, calls[0][1])
        self.assertEqual(1, len(result.payload["products"]))
        product = result.payload["products"][0]
        self.assertEqual("Industrial CNC Controller IC-200", product["title"])
        self.assertEqual("https://cnc.en.made-in-china.com/product/ic200.html", product["productUrl"])
        self.assertEqual("Shenzhen CNC Factory", product["supplierName"])
        self.assertEqual("USD", product["currency"])
        self.assertEqual([], product["contacts"])
        self.assertEqual(["https://image.made-in-china.com/ic200.jpg"], product["images"])
        self.assertEqual("US$ 120-150", product["attributes"]["madeInChinaPriceText"])
        self.assertEqual("10 Pieces", product["attributes"]["moq"])
        self.assertEqual("Guangdong, China", product["attributes"]["supplierLocation"])
        self.assertEqual("Manufacturer/Factory", product["attributes"]["businessType"])
        self.assertEqual("made-in-china", product["attributes"]["sourcePlatform"])

    def test_made_in_china_connector_detects_captcha(self):
        connector = MadeInChinaSearchConnector(http_get=lambda _url, _timeout: (200, "fcaptcha captcha.vemic.com"))

        result = connector.research("bluetooth speaker")

        self.assertFalse(result.success)
        self.assertIn("captcha", result.error_message.lower())

    def test_made_in_china_connector_reports_http_failure(self):
        connector = MadeInChinaSearchConnector(http_get=lambda _url, _timeout: (503, "unavailable"))

        result = connector.research("bluetooth speaker")

        self.assertFalse(result.success)
        self.assertIn("HTTP 503", result.error_message)

    def test_mcp_http_client_uses_json_rpc_tool_call(self):
        posts = []

        def http_post(url, payload, headers, timeout):
            posts.append((url, payload, headers, timeout))
            if payload["method"] == "initialize":
                return 200, {"Mcp-Session-Id": "session-1"}, json_response(
                    payload["id"], {"serverInfo": {"name": "playwright"}}
                )
            if payload["method"] == "notifications/initialized":
                return 202, {}, ""
            return 200, {}, json_response(payload["id"], {"content": [{"type": "text", "text": "{}"}]})

        client = McpHttpClient("http://browser-mcp:8931/mcp", http_post=http_post)
        result = client.call_tool("browser_navigate", {"url": "https://supplier.test"})

        self.assertEqual({"content": [{"type": "text", "text": "{}"}]}, result)
        self.assertEqual("initialize", posts[0][1]["method"])
        self.assertEqual("tools/call", posts[2][1]["method"])
        self.assertEqual("browser_navigate", posts[2][1]["params"]["name"])
        self.assertEqual("session-1", posts[2][2]["Mcp-Session-Id"])

    def test_mcp_http_client_selects_matching_sse_response(self):
        def http_post(url, payload, headers, timeout):
            if payload["method"] == "initialize":
                return 200, {"Mcp-Session-Id": "session-1"}, json_response(
                    payload["id"], {"serverInfo": {"name": "playwright"}}
                )
            if payload["method"] == "notifications/initialized":
                return 202, {}, ""
            body = (
                'event: message\n'
                'data: {"jsonrpc":"2.0","method":"notifications/progress","params":{}}\n\n'
                'event: message\n'
                f'data: {json_response(payload["id"], {"content": [{"type": "text", "text": "{}"}]})}\n\n'
            )
            return 200, {}, body

        client = McpHttpClient("http://browser-mcp:8931/mcp", http_post=http_post)
        result = client.call_tool("browser_evaluate", {"function": "() => ({})"})

        self.assertEqual({"content": [{"type": "text", "text": "{}"}]}, result)

    def test_split_args_removes_windows_path_quotes(self):
        args = _split_args('--yes @playwright/mcp@latest --executable-path "C:\\Program Files\\Google\\Chrome\\chrome.exe"')

        self.assertEqual("C:\\Program Files\\Google\\Chrome\\chrome.exe", args[-1])

    def test_parse_mcp_tool_json_accepts_text_content(self):
        payload = parse_mcp_tool_json(
            {"content": [{"type": "text", "text": '```json\n{"links": []}\n```'}]}
        )

        self.assertEqual({"links": []}, payload)

    def test_parse_mcp_tool_json_accepts_playwright_result_blocks(self):
        payload = parse_mcp_tool_json(
            {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            '### Result\n[{"title":"E2E UAV Flight Controller FC-100",'
                            '"url":"https://supplier.test/products/fc-100.html"}]\n'
                            "### Ran Playwright code\n```js\nawait page.evaluate(() => []);\n```"
                        ),
                    }
                ]
            }
        )

        self.assertEqual(
            [{"title": "E2E UAV Flight Controller FC-100", "url": "https://supplier.test/products/fc-100.html"}],
            payload,
        )

    def test_product_extraction_script_reads_real_page_hints(self):
        for expected in [
            'application/ld+json',
            'og:title',
            'itemprop="price"',
            'mailto:',
            'data-cfemail',
            'contactLinks',
            't.me/',
            'normalizePrice',
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, EXTRACT_PRODUCT_CODE)

    def test_playwright_mcp_browser_connector_extracts_products(self):
        client = FakeMcpClient(
            [
                {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                '{"links":[{"title":"E2E UAV Flight Controller FC-100",'
                                '"url":"https://supplier.test/products/fc-100.html"}]}'
                            ),
                        }
                    ]
                },
                {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                '{"title":"E2E UAV Flight Controller FC-100",'
                                '"productUrl":"https://supplier.test/products/fc-100.html",'
                                '"price":"120.00","currency":"USD",'
                                '"supplierName":"E2E Supplier Email Division",'
                                '"contacts":[{"type":"email","value":"supplier@example.test"}]}'
                            ),
                        }
                    ]
                },
            ]
        )
        connector = PlaywrightMcpBrowserConnector(
            mcp_client_factory=lambda: client,
            supplier_site_url="https://supplier.test",
            allowed_domains={"supplier.test"},
        )

        result = connector.research("E2E UAV Flight Controller FC-100 site:https://supplier.test")

        self.assertTrue(result.success, result.error_message)
        self.assertEqual(1, len(result.payload["products"]))
        self.assertEqual("E2E UAV Flight Controller FC-100", result.payload["products"][0]["title"])
        self.assertTrue(client.initialized)
        self.assertTrue(client.closed)
        navigate_calls = [call for call in client.calls if call[0] == "browser_navigate"]
        evaluate_calls = [call for call in client.calls if call[0] == "browser_evaluate"]
        self.assertEqual("https://supplier.test", navigate_calls[0][1]["url"])
        self.assertEqual("https://supplier.test/products/fc-100.html", navigate_calls[1][1]["url"])
        self.assertEqual(2, len(evaluate_calls))
        self.assertIn("function", evaluate_calls[0][1])
        self.assertIn("function", evaluate_calls[1][1])
        self.assertEqual("browser_close", client.calls[-1][0])

    def test_playwright_mcp_browser_connector_uses_search_engine_for_internet_mode(self):
        client = FakeMcpClient(
            [
                {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                '[{"title":"Industrial CNC Controller IC-200",'
                                '"url":"https://duckduckgo.com/l/?uddg=https%3A%2F%2Fsupplier.example%2Fproducts%2Fic-200"}]'
                            ),
                        }
                    ]
                },
                {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                '{"title":"Industrial CNC Controller IC-200",'
                                '"productUrl":"https://supplier.example/products/ic-200",'
                                '"price":"840.00","currency":"USD",'
                                '"supplierName":"Supplier Example","contacts":[]}'
                            ),
                        }
                    ]
                },
            ]
        )
        connector = PlaywrightMcpBrowserConnector(
            mcp_client_factory=lambda: client,
            supplier_site_url="https://supplier.test",
            allowed_domains={"duckduckgo.com"},
            research_mode="internet",
            allow_public_internet=True,
            search_url_template="https://duckduckgo.com/html/?q={query}",
        )

        result = connector.research("Industrial CNC Controller IC-200")

        self.assertTrue(result.success, result.error_message)
        navigate_calls = [call for call in client.calls if call[0] == "browser_navigate"]
        self.assertIn("Industrial%20CNC%20Controller", navigate_calls[0][1]["url"])
        self.assertEqual("https://supplier.example/products/ic-200", navigate_calls[1][1]["url"])
        self.assertEqual("internet", result.payload["source"]["mode"])
        self.assertEqual(1, len(result.payload["products"]))

    def test_playwright_mcp_browser_connector_prioritizes_product_result_links(self):
        client = FakeMcpClient(
            [
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                [
                                    {
                                        "title": "Raspberry Pi category",
                                        "url": "https://supplier.example/category/raspberry-pi",
                                    },
                                    {
                                        "title": "Raspberry Pi 5 - 16 GB RAM",
                                        "url": "https://supplier.example/product/6125",
                                    },
                                    {
                                        "title": "Raspberry Pi 5 - 8 GB RAM",
                                        "url": "https://supplier.example/product/5813",
                                    },
                                ]
                            ),
                        }
                    ]
                },
                {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                '{"title":"Raspberry Pi 5 - 8 GB RAM",'
                                '"productUrl":"https://supplier.example/product/5813",'
                                '"price":"80.00","currency":"USD",'
                                '"supplierName":"Supplier Example","contacts":[]}'
                            ),
                        }
                    ]
                },
            ]
        )
        connector = PlaywrightMcpBrowserConnector(
            mcp_client_factory=lambda: client,
            supplier_site_url="https://supplier.test",
            allowed_domains=set(),
            max_pages=1,
            research_mode="internet",
            allow_public_internet=True,
            search_url_template="https://supplier.example/search?q={query}",
        )

        result = connector.research("Raspberry Pi 5 8GB")

        self.assertTrue(result.success, result.error_message)
        navigate_calls = [call for call in client.calls if call[0] == "browser_navigate"]
        self.assertEqual("https://supplier.example/product/5813", navigate_calls[1][1]["url"])
        self.assertEqual(1, len(result.payload["products"]))

    def test_playwright_mcp_browser_connector_falls_back_to_search_link_when_product_page_fails(self):
        search_client = FakeMcpClient(
            [
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                [
                                    {
                                        "title": "Raspberry Pi 5 - 8 GB RAM $80.00",
                                        "url": "https://supplier.example/product/5813",
                                    },
                                ]
                            ),
                        }
                    ]
                },
            ]
        )
        product_client = ProductNavigateFailClient([])
        clients = iter([search_client, product_client])
        connector = PlaywrightMcpBrowserConnector(
            mcp_client_factory=lambda: next(clients),
            supplier_site_url="https://supplier.test",
            allowed_domains=set(),
            max_pages=1,
            research_mode="internet",
            allow_public_internet=True,
            search_url_template="https://supplier.example/search?q={query}",
        )

        result = connector.research("Raspberry Pi 5 8GB")

        self.assertTrue(result.success, result.error_message)
        self.assertEqual("Raspberry Pi 5 - 8 GB RAM $80.00", result.payload["products"][0]["title"])
        self.assertEqual("80.00", result.payload["products"][0]["price"])
        self.assertEqual("USD", result.payload["products"][0]["currency"])
        self.assertEqual("search_result_link", result.payload["products"][0]["attributes"]["extractionFallback"])
        self.assertEqual(1, len(result.payload["source"]["candidateErrors"]))

    def test_playwright_mcp_browser_connector_keeps_site_queries_bounded_in_internet_mode(self):
        client = FakeMcpClient(
            [
                {"content": [{"type": "text", "text": "[]"}]},
            ]
        )
        connector = PlaywrightMcpBrowserConnector(
            mcp_client_factory=lambda: client,
            supplier_site_url="https://supplier.test",
            allowed_domains={"supplier.test"},
            research_mode="internet",
            allow_public_internet=True,
        )

        result = connector.research("Flight controller site:https://supplier.test")

        self.assertTrue(result.success, result.error_message)
        self.assertEqual("https://supplier.test", client.calls[0][1]["url"])
        self.assertEqual("site", result.payload["source"]["mode"])

    def test_playwright_mcp_browser_connector_rejects_disallowed_domain(self):
        connector = PlaywrightMcpBrowserConnector(
            mcp_client_factory=lambda: FakeMcpClient([]),
            supplier_site_url="https://supplier.test",
            allowed_domains={"supplier.test"},
        )

        with self.assertRaises(BrowserSecurityError):
            connector.ensure_allowed_url("https://internal.example.local/products/1")

    def test_playwright_mcp_browser_connector_blocks_private_public_internet_targets(self):
        connector = PlaywrightMcpBrowserConnector(
            mcp_client_factory=lambda: FakeMcpClient([]),
            supplier_site_url="https://supplier.test",
            allowed_domains={"supplier.test"},
            research_mode="internet",
            allow_public_internet=True,
        )

        for url in [
            "http://127.0.0.1/admin",
            "http://10.0.0.5/products",
            "http://192.168.1.20/products",
            "http://metadata.internal/products",
            "http://service.local/products",
        ]:
            with self.subTest(url=url):
                with self.assertRaises(BrowserSecurityError):
                    connector.ensure_allowed_url(url)

        connector.ensure_allowed_url("https://supplier-public.example/products/1")

    def test_playwright_mcp_browser_connector_reports_tool_error(self):
        client = ToolErrorMcpClient()
        connector = PlaywrightMcpBrowserConnector(
            mcp_client_factory=lambda: client,
            supplier_site_url="https://supplier.test",
            allowed_domains={"supplier.test"},
        )

        result = connector.research("E2E UAV Flight Controller FC-100")

        self.assertFalse(result.success)
        self.assertIn("Chromium distribution", result.error_message)
        self.assertTrue(client.closed)

    def test_searxng_web_search_connector_parses_results(self):
        gets = []

        def http_get(url, timeout):
            gets.append((url, timeout))
            return 200, json.dumps(
                {
                    "results": [
                        {
                            "title": "Raspberry Pi 5 - 8 GB RAM",
                            "url": "https://supplier.example/product/5813",
                            "content": "Single-board computer",
                            "engine": "bing",
                            "score": 3.2,
                        },
                        {"title": "", "url": "https://supplier.example/empty"},
                    ]
                }
            )

        connector = SearxngWebSearchConnector(
            search_url="http://searxng:8080/search",
            result_limit=10,
            timeout_seconds=15,
            http_get=http_get,
        )

        results = connector.search("Raspberry Pi 5 8GB")

        self.assertIn("q=Raspberry+Pi+5+8GB", gets[0][0])
        self.assertIn("format=json", gets[0][0])
        self.assertEqual(1, len(results))
        self.assertEqual("https://supplier.example/product/5813", results[0].url)
        self.assertEqual("Single-board computer", results[0].snippet)

    def test_duckduckgo_html_web_search_connector_parses_results(self):
        gets = []

        def http_get(url, timeout):
            gets.append((url, timeout))
            return 200, """
                <html><body>
                  <a class="result__a" href="/l/?uddg=https%3A%2F%2Fsupplier.example%2Fproduct%2F5813">
                    Raspberry Pi 5 - 8 GB RAM
                  </a>
                  <a class="result__a" href="https://supplier.example/category/raspberry">
                    Raspberry Pi category
                  </a>
                </body></html>
            """

        connector = DuckDuckGoHtmlWebSearchConnector(
            search_url="https://duckduckgo.com/html/",
            result_limit=1,
            timeout_seconds=15,
            http_get=http_get,
        )

        results = connector.search("Raspberry Pi 5 8GB")

        self.assertIn("q=Raspberry+Pi+5+8GB", gets[0][0])
        self.assertEqual(1, len(results))
        self.assertEqual("https://supplier.example/product/5813", results[0].url)
        self.assertEqual("duckduckgo", results[0].engine)

    def test_web_search_factory_supports_duckduckgo_provider(self):
        settings = make_settings(
            web_search_provider="duckduckgo",
            web_search_url="https://duckduckgo.com/html/",
        )

        connector = build_web_search_connector(settings)

        self.assertIsInstance(connector, DuckDuckGoHtmlWebSearchConnector)

    def test_multi_engine_web_search_merges_unique_urls(self):
        first = FakeWebSearch(
            [
                WebSearchResult("Product A", "https://supplier.example/product/a#details", engine="engine-a"),
                WebSearchResult("Product B", "https://supplier.example/product/b", engine="engine-a"),
            ]
        )
        second = FakeWebSearch(
            [
                WebSearchResult("Product A duplicate", "https://supplier.example/product/a", engine="engine-b"),
                WebSearchResult("Product C", "https://other.example/product/c", engine="engine-b"),
            ]
        )
        connector = MultiEngineWebSearchConnector([first, second])

        results = connector.search("iphone 16")

        self.assertEqual(["iphone 16"], first.queries)
        self.assertEqual(["iphone 16"], second.queries)
        self.assertEqual(
            [
                "https://supplier.example/product/a",
                "https://supplier.example/product/b",
                "https://other.example/product/c",
            ],
            [result.url for result in results],
        )

    def test_multi_engine_web_search_uses_successful_engine_when_one_fails(self):
        failing = FailingWebSearch("<urlopen error [WinError 10061] connection refused>")
        healthy = FakeWebSearch(
            [
                WebSearchResult("Product C", "https://supplier.example/product/c", engine="engine-b"),
            ]
        )
        connector = MultiEngineWebSearchConnector([failing, healthy])

        results = connector.search("Регулятор iFlight BLITZ E80")

        self.assertEqual(["Регулятор iFlight BLITZ E80"], failing.queries)
        self.assertEqual(["Регулятор iFlight BLITZ E80"], healthy.queries)
        self.assertEqual(["https://supplier.example/product/c"], [result.url for result in results])

    def test_multi_engine_web_search_fails_when_all_engines_fail(self):
        connector = MultiEngineWebSearchConnector(
            [
                FailingWebSearch("engine-a unavailable"),
                FailingWebSearch("engine-b unavailable"),
            ]
        )

        with self.assertRaisesRegex(RuntimeError, "all web search engines failed"):
            connector.search("Регулятор iFlight BLITZ E80")

    def test_web_search_factory_supports_multi_engine_provider(self):
        settings = make_settings(
            web_search_provider="multi",
            web_search_engines="duckduckgo:https://duckduckgo.com/html/,searxng:http://searxng:8080/search",
        )

        connector = build_web_search_connector(settings)

        self.assertIsInstance(connector, MultiEngineWebSearchConnector)
        self.assertIsInstance(connector.engines[0], DuckDuckGoHtmlWebSearchConnector)
        self.assertIsInstance(connector.engines[1], SearxngWebSearchConnector)

    def test_ai_internet_product_search_uses_model_queries_and_candidate_selection(self):
        model = FakeModelProvider(
            [
                {"queries": ["raspberry pi 5 8gb buy", "raspberry pi 5 supplier"]},
                {
                    "selected": [
                        {
                            "title": "Raspberry Pi 5 - 8 GB RAM",
                            "url": "https://supplier.example/product/5813",
                            "reason": "exact product page",
                        }
                    ]
                },
            ]
        )
        web_search = FakeWebSearch(
            [
                WebSearchResult(
                    title="Raspberry Pi 5 - 8 GB RAM",
                    url="https://supplier.example/product/5813",
                    snippet="Product page",
                ),
                WebSearchResult(
                    title="Raspberry Pi category",
                    url="https://supplier.example/category/raspberry",
                    snippet="Category page",
                ),
            ]
        )
        browser = PlaywrightMcpBrowserConnector(
            mcp_client_factory=lambda: FakeMcpClient(
                [
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    '{"title":"Raspberry Pi 5 - 8 GB RAM",'
                                    '"productUrl":"https://supplier.example/product/5813",'
                                    '"price":"80.00","currency":"USD",'
                                    '"supplierName":"Supplier Example","contacts":[]}'
                                ),
                            }
                        ]
                    }
                ]
            ),
            supplier_site_url="https://supplier.test",
            allowed_domains=set(),
            allow_public_internet=True,
        )
        connector = AiInternetProductSearchConnector(
            model_provider=model,
            web_search=web_search,
            browser_connector=browser,
            query_count=2,
            candidate_limit=1,
        )

        result = connector.research("Raspberry Pi 5 8GB")

        self.assertTrue(result.success, result.error_message)
        self.assertEqual(["raspberry pi 5 8gb buy", "raspberry pi 5 supplier"], web_search.queries)
        self.assertIn("Generate", model.prompts[0])
        self.assertIn("Select", model.prompts[1])
        self.assertEqual("ai_internet", result.payload["source"]["mode"])
        self.assertEqual(1, len(result.payload["products"]))

    def test_ai_internet_product_search_expands_b2b_supplier_queries(self):
        model = FakeModelProvider([{"queries": ["Raspberry Pi 5 official supplier"]}, {"selected": []}])
        web_search = FakeWebSearch([])
        browser = PlaywrightMcpBrowserConnector(
            mcp_client_factory=lambda: FakeMcpClient([]),
            supplier_site_url="https://supplier.test",
            allowed_domains=set(),
            allow_public_internet=True,
        )
        connector = AiInternetProductSearchConnector(
            model_provider=model,
            web_search=web_search,
            browser_connector=browser,
            query_count=8,
            candidate_limit=1,
        )

        result = connector.research("Raspberry Pi 5 8GB", max_results=1)

        self.assertTrue(result.success, result.error_message)
        searched = " ".join(web_search.queries).lower()
        for expected in ["supplier", "manufacturer", "distributor", "wholesale", "moq", "stock", "contact"]:
            with self.subTest(expected=expected):
                self.assertIn(expected, searched)

    def test_ai_internet_product_search_prefers_real_supplier_candidates(self):
        model = FailingModelProvider()
        web_search = FakeWebSearch(
            [
                WebSearchResult("Raspberry Pi review blog", "https://blog.example/articles/raspberry-pi-review"),
                WebSearchResult("Raspberry Pi 5 distributor stock", "https://supplier.example/products/raspberry-pi-5"),
                WebSearchResult("Login", "https://supplier.example/login"),
            ]
        )
        browser = PlaywrightMcpBrowserConnector(
            mcp_client_factory=lambda: FakeMcpClient(
                [
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    '{"title":"Raspberry Pi 5 distributor stock",'
                                    '"productUrl":"https://supplier.example/products/raspberry-pi-5",'
                                    '"price":"80.00","currency":"USD",'
                                    '"supplierName":"Supplier Example","contacts":[]}'
                                ),
                            }
                        ]
                    }
                ]
            ),
            supplier_site_url="https://supplier.test",
            allowed_domains=set(),
            allow_public_internet=True,
        )
        connector = AiInternetProductSearchConnector(
            model_provider=model,
            web_search=web_search,
            browser_connector=browser,
            query_count=1,
            candidate_limit=1,
        )

        result = connector.research("Raspberry Pi 5", max_results=1)

        self.assertTrue(result.success, result.error_message)
        product = result.payload["products"][0]
        self.assertEqual("https://supplier.example/products/raspberry-pi-5", product["productUrl"])
        self.assertEqual("distributor", product["attributes"]["supplierType"])
        self.assertGreaterEqual(int(product["attributes"]["sourceConfidence"]), 70)

    def test_ai_internet_product_search_enriches_contacts_from_supplier_domain(self):
        model = FailingModelProvider()
        web_search = FakeWebSearch(
            [
                WebSearchResult(
                    "Industrial controller manufacturer",
                    "https://supplier.example/products/ic-200",
                    snippet="Manufacturer product page",
                )
            ]
        )
        client = UrlAwareMcpClient(
            {
                "https://supplier.example/products/ic-200": {
                    "title": "Industrial controller IC-200",
                    "productUrl": "https://supplier.example/products/ic-200",
                    "supplierName": "Supplier Example",
                    "contacts": [],
                    "attributes": {},
                },
                "https://supplier.example/contact": {
                    "title": "Contact Supplier Example",
                    "productUrl": "https://supplier.example/contact",
                    "supplierName": "Supplier Example",
                    "contacts": [{"type": "email", "value": "sales@supplier.example"}],
                    "attributes": {},
                },
            }
        )
        browser = PlaywrightMcpBrowserConnector(
            mcp_client_factory=lambda: client,
            supplier_site_url="https://supplier.test",
            allowed_domains=set(),
            allow_public_internet=True,
        )
        connector = AiInternetProductSearchConnector(
            model_provider=model,
            web_search=web_search,
            browser_connector=browser,
            query_count=1,
            candidate_limit=1,
        )

        result = connector.research("Industrial controller IC-200", max_results=1)

        self.assertTrue(result.success, result.error_message)
        product = result.payload["products"][0]
        self.assertEqual([{"type": "email", "value": "sales@supplier.example"}], product["contacts"])
        self.assertEqual("100", product["attributes"]["contactConfidence"])
        self.assertIn("https://supplier.example/contact", product["attributes"]["enrichmentPages"])

    def test_ai_internet_product_search_uses_page_contact_links_for_enrichment(self):
        model = FailingModelProvider()
        web_search = FakeWebSearch(
            [
                WebSearchResult(
                    "Sony headphones distributor stock",
                    "https://supplier.example/products/sony-headphones",
                    snippet="Distributor product page",
                )
            ]
        )
        client = UrlAwareMcpClient(
            {
                "https://supplier.example/products/sony-headphones": {
                    "title": "Sony headphones",
                    "productUrl": "https://supplier.example/products/sony-headphones",
                    "supplierName": "Supplier Example",
                    "contacts": [],
                    "attributes": {
                        "contactLinks": '["https://supplier.example/footer/contact-sales"]',
                    },
                },
                "https://supplier.example/footer/contact-sales": {
                    "title": "Contact sales",
                    "productUrl": "https://supplier.example/footer/contact-sales",
                    "supplierName": "Supplier Example",
                    "contacts": [{"type": "email", "value": "sales@supplier.example"}],
                    "attributes": {},
                },
            }
        )
        browser = PlaywrightMcpBrowserConnector(
            mcp_client_factory=lambda: client,
            supplier_site_url="https://supplier.test",
            allowed_domains=set(),
            allow_public_internet=True,
        )
        connector = AiInternetProductSearchConnector(
            model_provider=model,
            web_search=web_search,
            browser_connector=browser,
            query_count=1,
            candidate_limit=1,
        )

        result = connector.research("sony headphones", max_results=1)

        self.assertTrue(result.success, result.error_message)
        product = result.payload["products"][0]
        self.assertEqual([{"type": "email", "value": "sales@supplier.example"}], product["contacts"])
        self.assertIn("https://supplier.example/footer/contact-sales", product["attributes"]["enrichmentPages"])

    def test_ai_internet_product_search_fills_candidates_when_model_selects_too_few(self):
        model = FakeModelProvider(
            [
                {"queries": ["sony headphones supplier"]},
                {
                    "selected": [
                        {
                            "title": "Sony headphones supplier A",
                            "url": "https://supplier-a.example/products/sony-headphones",
                            "reason": "direct product page",
                        }
                    ]
                },
            ]
        )
        web_search = FakeWebSearch(
            [
                WebSearchResult("Sony headphones supplier A", "https://supplier-a.example/products/sony-headphones"),
                WebSearchResult("Sony headphones distributor stock", "https://supplier-b.example/products/sony-headphones"),
                WebSearchResult("Sony headphones manufacturer", "https://supplier-c.example/products/sony-headphones"),
            ]
        )
        client = UrlAwareMcpClient(
            {
                "https://supplier-a.example/products/sony-headphones": {
                    "title": "Sony headphones supplier A",
                    "productUrl": "https://supplier-a.example/products/sony-headphones",
                    "contacts": [],
                },
                "https://supplier-b.example/products/sony-headphones": {
                    "title": "Sony headphones supplier B",
                    "productUrl": "https://supplier-b.example/products/sony-headphones",
                    "contacts": [],
                },
                "https://supplier-c.example/products/sony-headphones": {
                    "title": "Sony headphones supplier C",
                    "productUrl": "https://supplier-c.example/products/sony-headphones",
                    "contacts": [],
                },
            }
        )
        browser = PlaywrightMcpBrowserConnector(
            mcp_client_factory=lambda: client,
            supplier_site_url="https://supplier.test",
            allowed_domains=set(),
            allow_public_internet=True,
        )
        connector = AiInternetProductSearchConnector(
            model_provider=model,
            web_search=web_search,
            browser_connector=browser,
            query_count=1,
            candidate_limit=1,
        )

        result = connector.research("sony headphones", max_results=3)

        self.assertTrue(result.success, result.error_message)
        self.assertEqual(3, result.payload["source"]["candidatesVisited"])
        self.assertEqual(3, len(result.payload["products"]))

    def test_ai_internet_product_search_uses_max_results_as_candidate_breadth(self):
        model = FailingModelProvider()
        web_search = FakeWebSearch(
            [
                WebSearchResult("Product A", "https://supplier.example/products/a"),
                WebSearchResult("Product B", "https://supplier.example/products/b"),
                WebSearchResult("Product C", "https://supplier.example/products/c"),
            ]
        )
        browser = PlaywrightMcpBrowserConnector(
            mcp_client_factory=lambda: FakeMcpClient(
                [
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    '{"title":"Candidate product",'
                                    '"productUrl":"https://supplier.example/products/candidate",'
                                    '"contacts":[]}'
                                ),
                            }
                        ]
                    }
                ]
            ),
            supplier_site_url="https://supplier.test",
            allowed_domains=set(),
            allow_public_internet=True,
            max_pages=10,
        )
        connector = AiInternetProductSearchConnector(
            model_provider=model,
            web_search=web_search,
            browser_connector=browser,
            query_count=1,
            candidate_limit=1,
        )

        result = connector.research("iphone 16", max_results=3)

        self.assertTrue(result.success, result.error_message)
        self.assertEqual(3, result.payload["source"]["candidatesVisited"])

    def test_ai_internet_product_search_stops_after_enough_products(self):
        model = FailingModelProvider()
        web_search = FakeWebSearch(
            [
                WebSearchResult("Product A supplier", "https://supplier.example/products/a"),
                WebSearchResult("Product B supplier", "https://supplier.example/products/b"),
                WebSearchResult("Product C supplier", "https://supplier.example/products/c"),
            ]
        )
        client = UrlAwareMcpClient(
            {
                "https://supplier.example/products/a": {
                    "title": "Product A",
                    "productUrl": "https://supplier.example/products/a",
                    "contacts": [{"type": "email", "value": "a@supplier.example"}],
                },
                "https://supplier.example/products/b": {
                    "title": "Product B",
                    "productUrl": "https://supplier.example/products/b",
                    "contacts": [{"type": "email", "value": "b@supplier.example"}],
                },
                "https://supplier.example/products/c": {
                    "title": "Product C",
                    "productUrl": "https://supplier.example/products/c",
                    "contacts": [{"type": "email", "value": "c@supplier.example"}],
                },
            }
        )
        browser = PlaywrightMcpBrowserConnector(
            mcp_client_factory=lambda: client,
            supplier_site_url="https://supplier.test",
            allowed_domains=set(),
            allow_public_internet=True,
            max_pages=10,
        )
        connector = AiInternetProductSearchConnector(
            model_provider=model,
            web_search=web_search,
            browser_connector=browser,
            query_count=1,
            candidate_limit=10,
        )

        result = connector.research("Product supplier", max_results=1)

        self.assertTrue(result.success, result.error_message)
        self.assertEqual(1, result.payload["source"]["candidatesVisited"])
        self.assertEqual(1, len(result.payload["products"]))

    def test_contact_enrichment_can_be_disabled_for_fast_search(self):
        client = UrlAwareMcpClient(
            {
                "https://supplier.example/products/a": {
                    "title": "Product A",
                    "productUrl": "https://supplier.example/products/a",
                    "contacts": [],
                    "attributes": {"contactLinks": '["https://supplier.example/contact"]'},
                },
                "https://supplier.example/contact": {
                    "title": "Contact",
                    "productUrl": "https://supplier.example/contact",
                    "contacts": [{"type": "email", "value": "sales@supplier.example"}],
                },
            }
        )
        browser = PlaywrightMcpBrowserConnector(
            mcp_client_factory=lambda: client,
            supplier_site_url="https://supplier.test",
            allowed_domains=set(),
            allow_public_internet=True,
            contact_enrichment_pages=0,
        )

        result = browser.extract_products_from_links(
            [{"title": "Product A", "url": "https://supplier.example/products/a"}],
            max_results=1,
        )

        self.assertEqual([], result["products"][0]["contacts"])
        self.assertNotIn("https://supplier.example/contact", [call[1].get("url") for call in client.calls])

    def test_ai_internet_product_search_falls_back_when_model_json_is_invalid(self):
        model = FailingModelProvider()
        web_search = FakeWebSearch(
            [
                WebSearchResult(
                    title="Industrial CNC Controller IC-200",
                    url="https://supplier.example/products/ic-200",
                    snippet="Product page",
                ),
            ]
        )
        browser = PlaywrightMcpBrowserConnector(
            mcp_client_factory=lambda: FakeMcpClient(
                [
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    '{"title":"Industrial CNC Controller IC-200",'
                                    '"productUrl":"https://supplier.example/products/ic-200",'
                                    '"price":"840.00","currency":"USD",'
                                    '"supplierName":"Supplier Example","contacts":[]}'
                                ),
                            }
                        ]
                    }
                ]
            ),
            supplier_site_url="https://supplier.test",
            allowed_domains=set(),
            allow_public_internet=True,
        )
        connector = AiInternetProductSearchConnector(
            model_provider=model,
            web_search=web_search,
            browser_connector=browser,
            query_count=3,
            candidate_limit=1,
        )

        result = connector.research("Industrial CNC Controller IC-200")

        self.assertTrue(result.success, result.error_message)
        self.assertEqual(
            [
                "Industrial CNC Controller IC-200",
                "Industrial CNC Controller IC-200 supplier",
                "Industrial CNC Controller IC-200 manufacturer",
            ],
            web_search.queries,
        )
        self.assertEqual(2, len(model.prompts))
        self.assertEqual(1, len(result.payload["products"]))

    def test_ai_internet_product_search_keeps_site_queries_bounded(self):
        model = FakeModelProvider([])
        web_search = FakeWebSearch([])
        browser = PlaywrightMcpBrowserConnector(
            mcp_client_factory=lambda: FakeMcpClient([{"content": [{"type": "text", "text": "[]"}]}]),
            supplier_site_url="https://supplier.test",
            allowed_domains={"supplier.test"},
        )
        connector = AiInternetProductSearchConnector(
            model_provider=model,
            web_search=web_search,
            browser_connector=browser,
        )

        result = connector.research("Flight controller site:https://supplier.test")

        self.assertTrue(result.success, result.error_message)
        self.assertEqual([], web_search.queries)
        self.assertEqual([], model.prompts)
        self.assertEqual("site", result.payload["source"]["mode"])

    def test_smtp_email_connector_sends_real_smtp_message(self):
        FakeSmtp.instances = []
        connector = SmtpEmailConnector(
            host="smtp.test",
            port=2525,
            username="user",
            password="super-secret",
            from_address="agent@example.test",
            use_tls=True,
            smtp_factory=FakeSmtp,
        )

        result = connector.send("supplier@example.test", "Product request", "Hello supplier")

        self.assertTrue(result.success, result.error_message)
        self.assertTrue(result.external_id)
        smtp = FakeSmtp.instances[0]
        self.assertEqual(("user", "super-secret"), smtp.logged_in)
        self.assertTrue(smtp.started_tls)
        self.assertEqual(1, len(smtp.messages))
        self.assertEqual("supplier@example.test", smtp.messages[0]["To"])
        self.assertEqual("agent@example.test", smtp.messages[0]["From"])
        self.assertEqual("Product request", smtp.messages[0]["Subject"])
        self.assertTrue(smtp.messages[0]["Date"])
        self.assertIn("providerTimestamp", result.payload)

    def test_smtp_email_connector_redacts_secret_from_errors(self):
        connector = SmtpEmailConnector(
            host="smtp.test",
            port=2525,
            username="user",
            password="super-secret",
            from_address="agent@example.test",
            smtp_factory=FailingSmtp,
        )

        result = connector.send("supplier@example.test", "Product request", "Hello supplier")

        self.assertFalse(result.success)
        self.assertNotIn("super-secret", result.error_message)
        self.assertIn("***REDACTED***", result.error_message)

    def test_gmail_imap_inbound_connector_fetches_unseen_messages(self):
        FakeImap.instances = []
        connector = GmailImapInboundConnector(
            host="imap.gmail.com",
            port=993,
            username="agent@example.test",
            password="gmail-app-password",
            mailbox="INBOX",
            imap_factory=FakeImap,
        )

        result = connector.fetch_unseen(limit=5)

        self.assertTrue(result.success, result.error_message)
        self.assertEqual(1, len(result.payload["messages"]))
        message = result.payload["messages"][0]
        self.assertIsInstance(message, InboundEmailMessage)
        self.assertEqual("supplier@example.test", message.from_address)
        self.assertEqual("agent@example.test", message.to_address)
        self.assertEqual("Re: Product request", message.subject)
        self.assertEqual("<gmail-inbound-1@example.test>", message.external_id)
        self.assertEqual("2026-05-02T15:55:53+00:00", message.provider_timestamp.astimezone(timezone.utc).isoformat())
        self.assertEqual("<gmail-outbound-1@example.test>", message.in_reply_to)
        self.assertIn("<gmail-outbound-1@example.test>", message.references)
        self.assertIn("MOQ is 10", message.body)
        self.assertEqual(("agent@example.test", "gmail-app-password"), FakeImap.instances[0].logged_in)
        self.assertTrue(FakeImap.instances[0].logged_out)

    def test_gmail_imap_inbound_connector_fetches_recent_messages_first(self):
        FakeImap.instances = []
        connector = GmailImapInboundConnector(
            host="imap.gmail.com",
            port=993,
            username="agent@example.test",
            password="gmail-app-password",
            mailbox="INBOX",
            imap_factory=ManyMessageImap,
        )

        result = connector.fetch_unseen(limit=2)

        self.assertTrue(result.success, result.error_message)
        self.assertEqual(
            ["<gmail-inbound-5@example.test>", "<gmail-inbound-4@example.test>"],
            [message.external_id for message in result.payload["messages"]],
        )

    def test_gmail_imap_inbound_connector_strips_quoted_reply_history(self):
        connector = GmailImapInboundConnector(
            host="imap.gmail.com",
            port=993,
            username="agent@example.test",
            password="gmail-app-password",
            mailbox="INBOX",
            imap_factory=QuotedReplyImap,
        )

        result = connector.fetch_unseen(limit=1)

        self.assertTrue(result.success, result.error_message)
        self.assertEqual("Здравствуйте, какую компанию вы представляете?", result.payload["messages"][0].body)

    def test_gmail_imap_inbound_connector_redacts_password_from_errors(self):
        connector = GmailImapInboundConnector(
            host="imap.gmail.com",
            port=993,
            username="agent@example.test",
            password="gmail-app-password",
            imap_factory=FailingImap,
        )

        result = connector.fetch_unseen(limit=5)

        self.assertFalse(result.success)
        self.assertNotIn("gmail-app-password", result.error_message)
        self.assertIn("***REDACTED***", result.error_message)

    def test_telegram_bot_connector_sends_real_api_message(self):
        posts = []

        def http_post(url, payload, timeout):
            posts.append((url, payload, timeout))
            return 200, '{"ok":true,"result":{"message_id":42}}'

        connector = TelegramBotConnector(
            bot_token="telegram-secret",
            default_chat_id="@supplier_e2e_test",
            http_post=http_post,
        )

        result = connector.send("@supplier_e2e_test", "Hello supplier")

        self.assertTrue(result.success, result.error_message)
        self.assertEqual("42", result.external_id)
        self.assertIn("bottelegram-secret/sendMessage", posts[0][0])
        self.assertEqual("@supplier_e2e_test", posts[0][1]["chat_id"])
        self.assertEqual("Hello supplier", posts[0][1]["text"])

    def test_telegram_bot_connector_redacts_token_from_errors(self):
        def http_post(url, payload, timeout):
            return 401, '{"ok":false,"description":"bad token telegram-secret"}'

        connector = TelegramBotConnector(
            bot_token="telegram-secret",
            default_chat_id="@supplier_e2e_test",
            http_post=http_post,
        )

        result = connector.send("@supplier_e2e_test", "Hello supplier")

        self.assertFalse(result.success)
        self.assertNotIn("telegram-secret", result.error_message)
        self.assertIn("***REDACTED***", result.error_message)

    def test_tool_registry_factory_registers_browser_email_and_telegram(self):
        settings = make_settings()
        registry = build_tool_registry(settings)

        self.assertIsNotNone(registry.require("browser_mcp"))
        self.assertIsNotNone(registry.require("email"))
        self.assertIsNotNone(registry.require("telegram"))

    def test_tool_registry_factory_registers_made_in_china_when_enabled(self):
        settings = make_settings(made_in_china_discovery_enabled=True)

        registry = build_tool_registry(settings)

        self.assertIsInstance(registry.require("made_in_china"), MadeInChinaSearchConnector)


if __name__ == "__main__":
    unittest.main()
