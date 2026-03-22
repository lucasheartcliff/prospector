<div align="center">

# ⛏️ Prospector

**Automated job search pipeline — LinkedIn scraping, ATS form automation,**  
**AI-powered cold outreach & Notion tracking.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Playwright](https://img.shields.io/badge/Playwright-1.x-2EAD33?style=flat-square&logo=playwright&logoColor=white)](https://playwright.dev)
[![n8n](https://img.shields.io/badge/n8n-self--hosted-EA4B71?style=flat-square&logo=n8n&logoColor=white)](https://n8n.io)
[![Claude](https://img.shields.io/badge/Claude-API-D4A017?style=flat-square)](https://anthropic.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

[Overview](#overview) · [Architecture](#architecture) · [Phases](#phases) · [Setup](#setup) · [Configuration](#configuration) · [Usage](#usage) · [Roadmap](#roadmap)

</div>

---

## Overview

Prospector is a self-hosted, modular pipeline that automates the full job search cycle — from discovering listings to submitting applications to sending personalized cold outreach — and tracks everything in a Notion dashboard.

Built for senior developers actively targeting international remote opportunities.

```
Daily cron
    │
    ├── JobSpy scraper ──────► n8n ──► Claude (tailor) ──► Notion DB
    │                                                           │
    ├── AIHawk (Easy Apply) ──────────────────────────────────►│
    │                                                           │
    ├── LinkedIn post scraper ──► Hunter.io ──► Claude (email) ──► Gmail ──►│
    │                                                           │
    └── Playwright ATS bot ─────────────────────────────────── ►│
                                                            Discord notify
```

### What it does

| Module | What it automates |
|--------|-------------------|
| **Easy Apply** | Submits LinkedIn Easy Apply forms daily using your Q&A config + Claude for dynamic answers |
| **Job Aggregation** | Scrapes LinkedIn, Indeed & Glassdoor via JobSpy, deduplicates, and logs new roles to Notion |
| **ATS Automation** | Fills and submits Greenhouse and Lever application forms via Playwright |
| **Post Outreach** | Detects hiring signals in LinkedIn posts, resolves contact emails, and sends AI-crafted cold emails via Gmail |
| **Tracking** | All activity is logged to a Notion pipeline database with status, follow-up dates, and Discord alerts |

---

## Architecture

Prospector is organized into five layers:

```
┌─────────────────────────────────────────────────────┐
│                   Orchestration Layer                │
│              n8n (self-hosted workflows)             │
└────────────┬───────────────────────────┬────────────┘
             │                           │
┌────────────▼──────────┐   ┌────────────▼────────────┐
│    Scraping Layer     │   │    Automation Layer      │
│  JobSpy · Playwright  │   │  AIHawk · FastAPI + PW   │
└────────────┬──────────┘   └────────────┬────────────┘
             │                           │
┌────────────▼───────────────────────────▼────────────┐
│                      AI Layer                        │
│          Anthropic Claude API (claude-sonnet)        │
└────────────────────────────┬────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────┐
│                    Data Layer                        │
│     Notion DB · Gmail · Discord · Local JSON logs    │
└─────────────────────────────────────────────────────┘
```

### Directory structure

```
prospector/
├── config/
│   ├── answers.yaml          # Master Q&A for form auto-fill
│   ├── config.yaml           # Keywords, schedules, rate limits
│   └── blacklist.yaml        # Companies to skip
├── scrapers/
│   ├── jobspy_scraper.py     # Multi-board job listing aggregation
│   └── linkedin_posts.py     # LinkedIn post hiring signal detector
├── ats/
│   ├── greenhouse.py         # Playwright script — Greenhouse ATS
│   ├── lever.py              # Playwright script — Lever ATS
│   └── workday.py            # Playwright script — Workday ATS (beta)
├── outreach/
│   ├── email_finder.py       # Hunter.io email resolution
│   └── email_generator.py    # Claude API cold email generator
├── orchestration/
│   └── server.py             # FastAPI webhook server for n8n triggers
├── assets/
│   ├── resume.pdf            # Your resume (gitignored)
│   └── resume.json           # JSON Resume schema (gitignored)
├── logs/                     # Structured JSON run logs (gitignored)
├── n8n/
│   └── workflows/            # Exported n8n workflow JSON files
├── .env.example
├── requirements.txt
└── README.md
```

---

## Phases

Prospector is implemented in six progressive phases. Each phase is independently useful.

### Phase 1 — Foundation
Prepare candidate assets and Notion pipeline database.
- `resume.pdf` + `resume.json` (JSON Resume schema)
- `answers.yaml` with all common application Q&A
- Notion **Job Applications** database (Company, Role, Source, Status, ATS Type, Follow-up Date)

### Phase 2 — LinkedIn Easy Apply
Automated batch submission of LinkedIn Easy Apply jobs via **AIHawk**.
- Configurable search filters (title, location, experience level)
- Claude API answers novel questions not covered by `answers.yaml`
- Hard cap: **25 applications/day**, randomized delay 3–8s

### Phase 3 — Job Aggregation
Daily multi-board scraping via **JobSpy** → n8n → Notion.
- Sources: LinkedIn, Indeed, Glassdoor
- Deduplication by job URL
- Claude generates a tailored 3-sentence candidate summary per new role
- ATS type auto-detected from application URL domain

### Phase 4 — ATS Form Automation
Playwright-based form submission for Greenhouse, Lever, and Workday.
- Exposed as local HTTP endpoints via FastAPI
- Triggered automatically by n8n on new Notion records
- Updates Notion status to `Applied` on success, `Failed` with error on failure

### Phase 5 — Active Post Outreach
Detects hiring intent in LinkedIn posts and sends personalized cold emails.
- Searches posts by configurable keyword queries (filtered to last 48h)
- Resolves contact email from LinkedIn profile → falls back to Hunter.io (≥70% confidence)
- Claude generates a <150-word personalized email per contact, referencing the post
- Sent via Gmail with `resume.pdf` attached, BCC to self
- Hard cap: **8 emails/day**
- Logs to Notion with follow-up date; Discord reminder if no reply in 5 days

### Phase 6 — Monitoring
Observability layer across all components.
- Discord notifications: batch completions, new high-match jobs, failures, follow-ups
- Structured JSON logs per script in `/logs/`
- Weekly Sunday summary report posted to Discord

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ (for n8n)
- n8n self-hosted instance
- Anthropic API key
- Hunter.io API key (free tier: 25 lookups/month)
- Gmail account with OAuth2 configured in n8n
- Notion account with an integration token

### 1. Clone & install

```bash
git clone https://github.com/yourusername/prospector.git
cd prospector

pip install -r requirements.txt
playwright install chromium
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
ANTHROPIC_API_KEY=sk-ant-...
HUNTER_API_KEY=...
NOTION_TOKEN=secret_...
NOTION_DATABASE_ID=...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
GMAIL_FROM_ADDRESS=you@gmail.com
RESUME_PDF_URL=https://drive.google.com/uc?id=...
```

### 3. Configure search parameters

Edit `config/config.yaml`:

```yaml
search:
  titles:
    - "Senior Java Developer"
    - "Senior Full Stack Engineer"
    - "Backend Engineer"
  locations:
    - "Remote"
    - "Europe"
  experience_level: "senior"

limits:
  easy_apply_daily: 25
  post_outreach_daily: 8
  claude_calls_daily: 200
  post_max_age_hours: 48
  hunter_min_confidence: 70

schedule:
  jobspy_cron: "0 8 * * *"       # 08:00 daily
  easy_apply_cron: "0 9 * * *"   # 09:00 daily
  post_scraper_cron: "0 10 * * *" # 10:00 daily
```

### 4. Fill in candidate Q&A

Edit `config/answers.yaml` with your personal details. See [answers.yaml reference](#answersyaml-reference) below.

### 5. Start the FastAPI webhook server

```bash
uvicorn orchestration.server:app --host 127.0.0.1 --port 8100
```

### 6. Import n8n workflows

Import all `.json` files from `n8n/workflows/` into your n8n instance and activate them.

### 7. First run — supervised mode

Before enabling full automation, run AIHawk in supervised mode:

```bash
DEBUG=true python -m aihawk --max-applications 10
```

Watch the first 10 applications and verify answer quality before increasing limits.

---

## Configuration

### `answers.yaml` reference

```yaml
personal:
  full_name: "Your Name"
  email: "you@example.com"
  phone: "+55 11 9xxxx-xxxx"
  linkedin_url: "https://linkedin.com/in/yourprofile"
  github_url: "https://github.com/yourusername"
  portfolio_url: ""

work:
  years_experience: 9
  current_company: "Current Employer"
  availability: "30 days"
  salary_expectation_usd: "7000-9000/month"
  work_authorization: "Brazilian national, open to relocation, available as PJ contractor"
  preferred_stack: [Java, Spring Boot, React, TypeScript, AWS]

answers:
  willing_to_relocate: true
  open_to_remote: true
  requires_visa_sponsorship: false
  cover_letter_default: |
    I am a senior software engineer with 9 years of experience...
```

### Rate limits

| Service | Default limit | Config key |
|---------|--------------|------------|
| LinkedIn Easy Apply | 25/day | `limits.easy_apply_daily` |
| Post outreach emails | 8/day | `limits.post_outreach_daily` |
| Claude API calls | 200/day | `limits.claude_calls_daily` |
| Hunter.io lookups | 25/day (free tier) | — |

---

## Usage

### Run individual components

```bash
# Scrape jobs from all boards and POST to n8n
python scrapers/jobspy_scraper.py

# Scrape LinkedIn posts for hiring signals
python scrapers/linkedin_posts.py

# Apply to a specific Greenhouse job
python ats/greenhouse.py --url "https://boards.greenhouse.io/company/jobs/123"

# Apply to a specific Lever job
python ats/lever.py --url "https://jobs.lever.co/company/abc-123"

# Generate and preview a cold email (dry run, no send)
python outreach/email_generator.py --post-url "https://linkedin.com/posts/..." --dry-run
```

### Notion pipeline

All application activity is tracked in the Notion **Job Applications** database:

| Field | Values |
|-------|--------|
| Status | `Queued` → `Applied` → `Emailed` → `Interview` → `Offer` / `Rejected` |
| Source | `LinkedIn Easy Apply`, `JobSpy`, `Post Outreach`, `Manual` |
| ATS Type | `Greenhouse`, `Lever`, `Workday`, `Other` |
| Follow-up Date | Auto-set to T+5 days for outreach records |

---

## Notes on LinkedIn ToS

Prospector interacts with LinkedIn through browser automation. LinkedIn's Terms of Service prohibit automated scraping and bulk actions. This project is intended for **personal use only** with conservative rate limits designed to minimize account risk. Use at your own discretion and responsibility.

---

## Roadmap

- [ ] Workday ATS full support (shadow DOM)
- [ ] Indeed direct application automation
- [ ] Reply detection via Gmail API to auto-update Notion status
- [ ] Scoring model for job-resume match (beyond keyword count)
- [ ] Web dashboard for pipeline metrics (Next.js)
- [ ] Docker Compose setup for full self-hosted deploy

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <sub>Built for the job hunt. Stop applying manually.</sub>
</div>
