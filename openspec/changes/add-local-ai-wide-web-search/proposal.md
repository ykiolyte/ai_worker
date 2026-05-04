## Why

The current live internet demo is bounded to one product-search site, so it
does not satisfy the product-sourcing goal of discovering suppliers across the
public web. The user also needs the search workflow to be driven by a local AI
model rather than only deterministic title matching.

## What Changes

- Add a local Ollama model provider for agent planning and ranking.
- Add a local SearXNG web-search connector so discovery is not tied to one
  supplier domain.
- Add an AI-assisted product research connector that:
  - asks the local model to generate web-search queries;
  - searches the public web through SearXNG;
  - asks the local model to rank and select likely product pages;
  - extracts selected pages through the existing Playwright Browser MCP
    connector;
  - validates all output before persistence.
- Keep controlled `site:<url>` queries compatible with the existing
  test-protocol contour.
- Add Docker Compose services and environment defaults for local Ollama and
  SearXNG.
- Document the local model setup and live-search commands.

## Capabilities

### New Capabilities

- `local-ai-model-provider`: Configure and call a local Ollama model for
  structured agent planning/ranking.
- `wide-web-product-search`: Discover product candidates across the public web
  through local metasearch and AI ranking.

### Modified Capabilities

- `agent-orchestration`: Product search tasks may use an AI-assisted research
  connector that combines local LLM planning, web search, and Browser MCP page
  extraction.
- `internet-product-search`: Internet mode must no longer be restricted to one
  configured supplier/search site when wide-web search is enabled.

## Impact

- Backend settings, model-provider factory, connector registry, search
  connector classes, and product-search worker runtime.
- Docker Compose services for `ollama` and `searxng`.
- Environment examples and development docs.
- Unit/contract tests for Ollama JSON handling, SearXNG result parsing,
  AI-assisted query generation/ranking, and controlled `site:` compatibility.
- Live verification requires Docker, Browser MCP, SearXNG, Ollama, and a pulled
  local model suitable for the available GPU.
