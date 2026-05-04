## Context

The current browser connector can extract product pages, but the live public
internet demo is anchored to a single `INTERNET_SEARCH_URL_TEMPLATE`. That is
useful for proving Browser MCP extraction, but it is not a real sourcing agent:
it does not search broadly and it does not use the configured model provider to
decide where to look.

A local LLM still needs an external discovery source because it does not contain
an up-to-date searchable index of the web. The target architecture is therefore
`local model -> web-search provider -> Browser MCP extraction -> validation`.

## Goals / Non-Goals

**Goals:**

- Run the model provider locally through Ollama.
- Use the local model to generate search queries and rank product candidates.
- Search beyond one fixed supplier site by using a configurable web-search
  provider; SearXNG is the self-hosted provider and DuckDuckGo HTML is the
  no-Docker local fallback.
- Keep Browser MCP as the extraction path for selected product pages.
- Keep `site:<url>` queries compatible with the controlled E2E supplier contour.
- Keep strict schema validation and public URL safety checks.
- Provide Docker Compose services and commands that can run on the user's RTX
  4070 SUPER class machine.

**Non-Goals:**

- No autonomous purchasing, checkout, login, captcha solving, or bypass.
- No guarantee that every website can be scraped; sites may block automation.
- No paid search API dependency in this slice.
- No fine-tuning or training a model.
- No change to supplier contact policy.

## Decisions

### Decision 1: Ollama As Local Model Runtime

Use an `OllamaModelProvider` over HTTP (`/api/generate`) with JSON prompts and
strict parsing. Docker Compose runs `ollama/ollama`; the default model is a
`mistral-nemo:12b` instruct model suitable for a 12 GB VRAM GPU and 32 GB RAM.

Rationale: Ollama is simple to run locally, keeps the provider behind the
existing `ModelProvider` abstraction, and avoids external model API keys.

### Decision 2: Configurable Web Discovery

Use a `WebSearchConnector` abstraction with SearXNG JSON for self-hosted
metasearch and DuckDuckGo HTML for no-Docker local runs. Docker Compose still
provides `searxng/searxng`, while `.env` can select `duckduckgo` when Docker is
unavailable.

Rationale: a local LLM is not a web index. SearXNG provides broad metasearch
without hardcoding one supplier domain into business logic, and DuckDuckGo HTML
keeps live development possible when Docker Desktop cannot run.

### Decision 3: AI-Assisted Research Connector

Add an `AiInternetProductSearchConnector` registered as the `browser_mcp` tool
when `BROWSER_RESEARCH_MODE=ai_internet`. It orchestrates:

1. model-generated search queries;
2. web-search result collection;
3. model ranking/selection of likely product pages;
4. Playwright MCP extraction for selected URLs;
5. existing validation/persistence.

Rationale: this makes the model responsible for search strategy and candidate
selection while preserving deterministic tool boundaries and validation.

### Decision 4: Preserve Controlled Site Mode

Any query containing `site:<url>` continues to use the bounded Playwright MCP
site path. This keeps `test_protocol.md` and local controlled supplier checks
stable.

Rationale: production-like acceptance still needs deterministic controlled
resources even while live sourcing can search broadly.

## Risks / Trade-offs

- Search engines may rate-limit SearXNG engines -> keep result limits low,
  expose provider settings, and persist partial results/errors.
- Local model may return invalid JSON -> parse defensively and fallback to
  conservative query/result selection while recording that fallback.
- Some product pages block Browser MCP -> preserve contactless/fallback product
  cards when configured.
- GPU passthrough may not be available in Docker Desktop -> Ollama can still run
  on CPU, but slowly; document GPU checks and commands.
- "Whole internet" is bounded by available search-engine results and public
  pages, not by private/logged-in/captcha-protected content.

## Migration Plan

1. Add config fields for Ollama and web search.
2. Add model and web-search connectors with tests.
3. Add AI-assisted research connector and register it in internet mode.
4. Add Docker Compose services and env defaults.
5. Pull the local model and run a live search.
6. Roll back by setting `BROWSER_RESEARCH_MODE=site` or `internet`.

## Open Questions

- Whether a larger CPU/GPU-offloaded model is worth the slower latency after
  the `mistral-nemo:12b` baseline is measured on the user's GPU.
- Whether a managed paid search API should be added later for production-grade
  reliability when SearXNG engines are rate-limited.
