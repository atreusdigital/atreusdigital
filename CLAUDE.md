# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Atreus Digital — Automatizaciones** is a multi-technology automation project covering:
- API integrations (CRMs, ERPs, SaaS platforms)
- Web scraping & data processing
- Notifications & alerts (email, Slack, WhatsApp, etc.)
- Automated reports & dashboards

## Repository Structure

```
AtreusDigital/
├── integrations/   # API connectors and third-party service integrations
├── scrapers/       # Web scraping and data extraction scripts
├── notifications/  # Alert and notification dispatchers
├── reports/        # Report generation and dashboard automation
├── shared/         # Shared utilities, config loaders, HTTP clients
└── scripts/        # One-off or scheduled run scripts
```

## Tech Stack

Mixed stack — choose the right tool per automation:
- **Python** — scraping (BeautifulSoup, Playwright), data processing (pandas), API clients (httpx/requests)
- **Node.js / TypeScript** — event-driven integrations, webhook handlers
- **Shell scripts** — cron jobs, orchestration glue

## Environment & Configuration

- Store all secrets and credentials in `.env` files (never commit them)
- Use a `.env.example` file to document required variables for each module
- Each subfolder may have its own `.env.example` if it has distinct dependencies

## Running Automations

Each automation should be self-contained and runnable as:
```bash
# Python
python integrations/<module>/main.py

# Node
node integrations/<module>/index.js

# With environment
cp .env.example .env && python scrapers/<module>/main.py
```

## Dependencies

- Python: use `requirements.txt` per module or a root-level one for shared deps
- Node: use `package.json` per module; prefer `pnpm` or `npm`
- Always pin dependency versions for reproducibility
