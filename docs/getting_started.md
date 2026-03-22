# Getting Started with Prospector

Step-by-step guide to set up and run the full pipeline.

---

## Prerequisites

- Python 3.11+
- Node.js 18+ (for n8n)
- A LinkedIn account
- API keys: Anthropic, Hunter.io, Notion, Discord webhook

---

## Step 1 — Install Dependencies

```bash
cd ~/projects/prospector

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install the project
pip install -e ".[dev]"

# Install Playwright browsers
playwright install chromium
```

---

## Step 2 — Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your real credentials:

```env
ANTHROPIC_API_KEY=sk-ant-...          # From console.anthropic.com
HUNTER_API_KEY=...                     # From hunter.io/api-keys
NOTION_TOKEN=secret_...                # From notion.so/my-integrations
NOTION_DATABASE_ID=...                 # See Step 3
DISCORD_WEBHOOK_URL=https://discord... # Server Settings → Integrations → Webhooks
GMAIL_FROM_ADDRESS=you@gmail.com
RESUME_PDF_URL=https://drive.google.com/uc?id=...
SERVER_PORT=8100
DEBUG=false
```

---

## Step 3 — Set Up Notion Database

1. Open Notion and create a new **full-page database** called "Job Applications"
2. Add these properties:

| Property | Type |
|----------|------|
| Company | Title (default) |
| Role | Text |
| URL | URL |
| Source | Select → add options: `JobSpy`, `LinkedIn Easy Apply`, `Post Outreach`, `Manual` |
| Status | Select → add options: `Queued`, `Applied`, `Emailed`, `Interview`, `Offer`, `Rejected`, `Failed`, `Manual Required` |
| ATS Type | Select → add options: `Greenhouse`, `Lever`, `Workday`, `Other`, `Easy Apply` |
| Summary | Text |
| Follow-up Date | Date |
| Contact Email | Email |
| Error | Text |

3. Create a **Board view** grouped by `Status`
4. Create a **Table view** filtered to "Applied in last 7 days", sorted by date descending
5. Go to **notion.so/my-integrations**, create an integration, and copy the token into `.env`
6. Share the database with your integration (click "..." → "Connect to" → your integration)
7. Copy the database ID from the URL: `notion.so/<workspace>/<DATABASE_ID>?v=...` → paste into `.env`

---

## Step 4 — Prepare Your Assets

### resume.json

Create `assets/resume.json` using the [JSON Resume](https://jsonresume.org/schema/) format:

```json
{
  "basics": {
    "name": "Your Name",
    "label": "Senior Software Engineer",
    "email": "you@example.com",
    "phone": "+55 11 9xxxx-xxxx",
    "url": "https://github.com/yourusername",
    "summary": "9 years of experience in Java, Spring Boot, React...",
    "location": { "city": "São Paulo", "countryCode": "BR" },
    "profiles": [
      { "network": "LinkedIn", "url": "https://linkedin.com/in/you" },
      { "network": "GitHub", "url": "https://github.com/you" }
    ]
  },
  "work": [...],
  "skills": [...]
}
```

### resume.pdf

Copy your resume PDF to `assets/resume.pdf`. This file is used for ATS uploads and email attachments.

### answers.yaml

Edit `config/answers.yaml` with your real information:

```yaml
personal:
  full_name: "Your Full Name"
  email: "you@example.com"
  phone: "+55 11 9xxxx-xxxx"
  linkedin_url: "https://linkedin.com/in/yourprofile"
  github_url: "https://github.com/yourusername"

work:
  years_experience: 9
  current_company: "Your Current Company"
  availability: "30 days"
  salary_expectation_usd: "7000-9000/month"
  work_authorization: "Brazilian national, available as PJ contractor"
  preferred_stack:
    - Java
    - Spring Boot
    - React
    - TypeScript
    - AWS

answers:
  willing_to_relocate: true
  open_to_remote: true
  requires_visa_sponsorship: false
  cover_letter_default: |
    I am a senior software engineer with 9 years of experience
    specializing in Java and Spring Boot...
```

---

## Step 5 — Configure Search Parameters

Edit `config/config.yaml` to match your job search:

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
```

Optionally add companies to skip in `config/blacklist.yaml`:

```yaml
companies:
  - "Company You Don't Want"
  - "Another Company"
```

---

## Step 6 — Test the JobSpy Scraper (Phase 3)

This is the best first test — it validates your config and populates Notion.

```bash
# Dry run — prints jobs to terminal without touching Notion
python -m scrapers.jobspy_scraper --dry-run

# Override titles for a quick test
python -m scrapers.jobspy_scraper --dry-run --titles "Backend Engineer"
```

If the dry run looks good, do a real run (requires n8n running — see Step 9):

```bash
python -m scrapers.jobspy_scraper
```

---

## Step 7 — Test ATS Automation (Phase 4)

### Start the FastAPI server

```bash
# Terminal 1
python -m orchestration.server

# Or with debug mode (shows browser window)
DEBUG=true python -m orchestration.server
```

Verify it's running:

```bash
curl http://127.0.0.1:8100/health
# → {"status":"ok"}
```

### Test a Greenhouse application

Find a test job posting on Greenhouse and run:

```bash
# Standalone (debug mode to watch the browser)
DEBUG=true python -m ats.greenhouse --url "https://boards.greenhouse.io/company/jobs/12345"

# Or via the API server
curl -X POST http://127.0.0.1:8100/apply \
  -H "Content-Type: application/json" \
  -d '{"url": "https://boards.greenhouse.io/company/jobs/12345", "ats_type": "Greenhouse", "notion_page_id": "your-page-id"}'
```

### Test a Lever application

```bash
DEBUG=true python -m ats.lever --url "https://jobs.lever.co/company/abc-123"
```

---

## Step 8 — Test Outreach (Phase 5)

### Generate a cold email (dry run)

```bash
python -m outreach.email_generator \
  --author "Jane Smith" \
  --company "TechCorp" \
  --post-content "We're hiring senior backend engineers to work on our distributed systems platform..." \
  --dry-run
```

### Find an email address

```bash
python -m outreach.email_finder \
  --profile-url "https://linkedin.com/in/janesmith" \
  --company-domain "techcorp.com" \
  --first-name "Jane" \
  --last-name "Smith"
```

### LinkedIn post scraping

First, export your LinkedIn cookies:

1. Log into LinkedIn in Chrome
2. Use an extension like "EditThisCookie" to export cookies as JSON
3. Save to `config/linkedin_cookies.json`

Then run:

```bash
# Dry run
python -m scrapers.linkedin_posts --dry-run

# With custom keywords
python -m scrapers.linkedin_posts --dry-run --keywords "hiring senior backend" "looking for java developer"
```

---

## Step 9 — Set Up n8n Workflows

### Install and start n8n

```bash
npm install -g n8n
n8n start
# n8n opens at http://localhost:5678
```

### Create the workflows

You need 4 workflows in n8n. Build them using the n8n visual editor:

#### Workflow 1 — Job Aggregation

```
Trigger: Webhook (POST /webhook/jobs)
  → Split In Batches (batch size: 1)
    → HTTP Request: GET Notion API — query database filtered by URL (dedup check)
    → IF (results.length == 0):
      → HTTP Request: POST Anthropic API — generate tailored summary
      → Set node: detect ATS type from URL domain
      → HTTP Request: POST Notion API — create page
      → IF (keyword match score >= 3):
        → HTTP Request: POST Discord webhook — notify high-match job
```

#### Workflow 2 — Easy Apply Summary

```
Trigger: Webhook (POST /webhook/easy-apply)
  → Split In Batches
    → HTTP Request: POST Notion API — create page (Source="LinkedIn Easy Apply", Status="Applied")
  → HTTP Request: POST Discord webhook — "Applied to N jobs via Easy Apply"
```

#### Workflow 3 — ATS Automation

```
Trigger: Notion Trigger (polling, filter: Status="Queued" AND ATS Type in ["Greenhouse","Lever"])
  → HTTP Request: POST localhost:8100/apply — {url, ats_type, notion_page_id}
  → IF success: POST Discord webhook
  → IF failure: POST Discord webhook with error
```

#### Workflow 4 — Post Outreach

```
Trigger: Webhook (POST /webhook/posts)
  → Split In Batches
    → Function node: check daily email count (< 8)
    → HTTP Request: POST localhost:8100/find-email
    → IF (email found AND verified):
      → HTTP Request: GET Notion API — dedup by contact email
      → IF (not exists):
        → HTTP Request: POST localhost:8100/generate-email
        → Gmail node: send email with resume.pdf attachment, BCC self
        → HTTP Request: POST Notion API — create page (Source="Post Outreach", Status="Emailed", Follow-up=+5 days)
        → HTTP Request: POST Discord webhook
```

Export each workflow to `n8n/workflows/` for backup:

```bash
./scripts/export_n8n_workflows.sh
```

---

## Step 10 — Schedule with Cron

Add these cron jobs to run the pipeline daily:

```bash
crontab -e
```

```cron
# JobSpy scraper — 8:00 AM daily
0 8 * * * cd /home/user/projects/prospector && .venv/bin/python -m scrapers.jobspy_scraper >> logs/cron.log 2>&1

# AIHawk Easy Apply — 9:00 AM daily (Mon-Fri)
0 9 * * 1-5 /home/user/projects/prospector/scripts/aihawk_wrapper.sh >> logs/cron.log 2>&1

# LinkedIn post scraper — 10:00 AM daily
0 10 * * * cd /home/user/projects/prospector && .venv/bin/python -m scrapers.linkedin_posts >> logs/cron.log 2>&1

# Weekly summary — Sunday 6:00 PM
0 18 * * 0 cd /home/user/projects/prospector && .venv/bin/python scripts/weekly_summary.py >> logs/cron.log 2>&1

# Export n8n workflows — Sunday midnight
0 0 * * 0 /home/user/projects/prospector/scripts/export_n8n_workflows.sh >> logs/cron.log 2>&1
```

---

## Step 11 — Set Up systemd Services (Optional)

For production reliability, use systemd instead of manually starting services:

```bash
# Copy service files (replace %i with your username)
sudo cp scripts/systemd/prospector-server.service /etc/systemd/system/prospector-server@.service
sudo cp scripts/systemd/n8n-watchdog.service /etc/systemd/system/n8n-watchdog@.service

# Enable and start
sudo systemctl enable --now prospector-server@$USER
sudo systemctl enable --now n8n-watchdog@$USER

# Check status
sudo systemctl status prospector-server@$USER
sudo systemctl status n8n-watchdog@$USER
```

---

## Step 12 — Set Up Discord Notifications

1. Go to your Discord server → **Server Settings** → **Integrations** → **Webhooks**
2. Create a webhook in your preferred channel (e.g., `#job-search`)
3. Copy the webhook URL into `.env` as `DISCORD_WEBHOOK_URL`

You'll receive notifications for:
- New high-match jobs discovered
- Easy Apply batch completions
- Outreach emails sent
- ATS automation failures
- Follow-up reminders
- Weekly pipeline summary

---

## Daily Operation

Once everything is set up, your daily workflow looks like this:

| Time | What happens | You do |
|------|-------------|--------|
| 08:00 | JobSpy scrapes LinkedIn/Indeed/Glassdoor → new jobs land in Notion | Review Notion board for interesting roles |
| 09:00 | AIHawk auto-applies to 25 Easy Apply jobs | Check Discord for completion summary |
| 10:00 | LinkedIn post scraper finds hiring posts → outreach emails sent | Review sent emails in Gmail "Sent" folder |
| Ongoing | n8n triggers Playwright for Greenhouse/Lever jobs in "Queued" status | Move interesting jobs to "Queued" to trigger auto-apply |
| Sunday | Weekly summary posted to Discord | Review pipeline stats |

### Manual actions you still need to do

- **Review Notion board** daily for new promising roles
- **Move jobs to "Queued"** if you want ATS automation to apply
- **Handle "Manual Required"** Workday jobs by applying yourself
- **Respond to replies** when companies get back to you
- **Update answers.yaml** when you encounter new form questions (check `logs/`)
- **Update blacklist.yaml** to skip companies you're not interested in

---

## Troubleshooting

### "Module not found" errors

Make sure you installed the project in editable mode:

```bash
pip install -e .
```

### JobSpy returns no results

- Check your search titles and locations in `config/config.yaml`
- Some boards may be temporarily unavailable — check logs

### ATS bot fails to submit

- Run with `DEBUG=true` to see the browser
- Form selectors may have changed — check `ats/greenhouse.py` or `ats/lever.py`
- The job may have closed or the form structure may be unusual

### LinkedIn scraping gets blocked

- Ensure your `config/linkedin_cookies.json` is up to date
- Reduce scraping frequency
- Use a residential IP if possible

### Claude API errors

- Check your API key in `.env`
- Check daily usage with: `cat logs/.rate_claude_$(date +%Y-%m-%d).json`
- Verify your Anthropic account has credits

### Notion API errors

- Verify the integration has access to the database
- Check that all property names match exactly (case-sensitive)
- Test with: `python -c "from common.notion_client import NotionJobsDB; import asyncio; asyncio.run(NotionJobsDB().query_by_url('test'))"`
