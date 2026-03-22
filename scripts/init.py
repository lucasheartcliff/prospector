#!/usr/bin/env python3
"""Prospector interactive setup wizard.

Walks through all configuration steps, collects user input,
creates config files, installs dependencies, and validates connections.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_DIR / "config"
ASSETS_DIR = PROJECT_DIR / "assets"
LOGS_DIR = PROJECT_DIR / "logs"

# ANSI colors
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
DIM = "\033[2m"
RESET = "\033[0m"


def banner():
    print(f"""
{CYAN}{BOLD}  ⛏️  Prospector — Setup Wizard{RESET}
{DIM}  Automated job search pipeline{RESET}
{DIM}  ─────────────────────────────{RESET}
""")


def step(number: int, title: str):
    print(f"\n{BOLD}{CYAN}━━━ Step {number} — {title} ━━━{RESET}\n")


def success(msg: str):
    print(f"  {GREEN}✔{RESET} {msg}")


def warn(msg: str):
    print(f"  {YELLOW}⚠{RESET} {msg}")


def error(msg: str):
    print(f"  {RED}✖{RESET} {msg}")


def info(msg: str):
    print(f"  {DIM}→{RESET} {msg}")


def ask(prompt: str, default: str = "", required: bool = False, secret: bool = False) -> str:
    """Prompt user for input with optional default."""
    suffix = f" [{default}]" if default else ""
    suffix += ": " if not secret else " (hidden): "

    while True:
        if secret:
            import getpass
            value = getpass.getpass(f"  {prompt}{suffix}")
        else:
            value = input(f"  {prompt}{suffix}").strip()

        if not value and default:
            return default
        if not value and required:
            error("This field is required.")
            continue
        return value


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    """Prompt user for yes/no."""
    hint = "Y/n" if default else "y/N"
    value = input(f"  {prompt} [{hint}]: ").strip().lower()
    if not value:
        return default
    return value in ("y", "yes")


def ask_list(prompt: str, default: list[str] | None = None) -> list[str]:
    """Prompt user for a comma-separated list."""
    default_str = ", ".join(default) if default else ""
    raw = ask(prompt, default=default_str)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _update_env_key(key: str, value: str):
    """Update or append a key in the .env file."""
    env_path = PROJECT_DIR / ".env"
    if not env_path.exists():
        env_path.write_text(f"{key}={value}\n")
        return
    content = env_path.read_text()
    lines = content.splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n")


def run(cmd: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a shell command."""
    return subprocess.run(
        cmd, shell=True, cwd=str(PROJECT_DIR),
        check=check, capture_output=capture, text=True,
    )


# ──────────────────────────────────────────────
# Steps
# ──────────────────────────────────────────────

def step_1_directories():
    """Ensure project directories exist."""
    step(1, "Project Structure")

    dirs = [CONFIG_DIR, ASSETS_DIR, LOGS_DIR, PROJECT_DIR / "n8n" / "workflows"]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        success(f"{d.relative_to(PROJECT_DIR)}/")

    # .gitkeep files
    for d in [ASSETS_DIR, LOGS_DIR, PROJECT_DIR / "n8n" / "workflows"]:
        gitkeep = d / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    success("Directory structure ready")


def step_2_venv():
    """Create virtual environment and install dependencies."""
    step(2, "Python Environment")

    venv_dir = PROJECT_DIR / ".venv"

    if venv_dir.exists():
        info("Virtual environment already exists at .venv/")
        reinstall = ask_yes_no("Reinstall dependencies?", default=False)
        if not reinstall:
            return
    else:
        info("Creating virtual environment...")
        run(f"{sys.executable} -m venv .venv")
        success("Virtual environment created at .venv/")

    # Determine pip path
    pip = str(venv_dir / "bin" / "pip")
    if not Path(pip).exists():
        pip = str(venv_dir / "Scripts" / "pip")  # Windows

    info("Installing dependencies (this may take a minute)...")
    result = run(f"{pip} install -e '.[dev]'", check=False, capture=True)
    if result.returncode != 0:
        error("pip install failed:")
        print(result.stderr[-500:] if result.stderr else "Unknown error")
        warn("You can retry manually: pip install -e '.[dev]'")
    else:
        success("Dependencies installed")

    info("Installing Playwright browsers...")
    python = str(venv_dir / "bin" / "python")
    if not Path(python).exists():
        python = str(venv_dir / "Scripts" / "python")
    result = run(f"{python} -m playwright install chromium", check=False, capture=True)
    if result.returncode == 0:
        success("Playwright Chromium installed")
    else:
        warn("Playwright install failed — run manually: playwright install chromium")


def step_3_api_keys() -> dict:
    """Collect API keys and create .env file."""
    step(3, "API Keys & Credentials")

    env_path = PROJECT_DIR / ".env"
    existing: dict[str, str] = {}

    if env_path.exists():
        info("Found existing .env file")
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                existing[key.strip()] = val.strip()
        if not ask_yes_no("Reconfigure API keys?", default=False):
            return existing

    print()
    info("Enter your API keys below. Press Enter to keep existing values.\n")

    keys = {
        "ANTHROPIC_API_KEY": ask(
            "Anthropic API key",
            default=existing.get("ANTHROPIC_API_KEY", ""),
            required=True,
            secret=True,
        ),
        "HUNTER_API_KEY": ask(
            "Hunter.io API key",
            default=existing.get("HUNTER_API_KEY", ""),
            secret=True,
        ),
        "NOTION_TOKEN": ask(
            "Notion integration token",
            default=existing.get("NOTION_TOKEN", ""),
            required=True,
            secret=True,
        ),
        "NOTION_DATABASE_ID": ask(
            "Notion database ID",
            default=existing.get("NOTION_DATABASE_ID", ""),
        ),
        "DISCORD_WEBHOOK_URL": ask(
            "Discord webhook URL",
            default=existing.get("DISCORD_WEBHOOK_URL", ""),
        ),
        "GMAIL_FROM_ADDRESS": ask(
            "Gmail address (for outreach)",
            default=existing.get("GMAIL_FROM_ADDRESS", ""),
        ),
        "RESUME_PDF_URL": ask(
            "Public URL for resume.pdf (e.g. Google Drive link)",
            default=existing.get("RESUME_PDF_URL", ""),
        ),
        "N8N_WEBHOOK_URL": ask(
            "n8n webhook base URL",
            default=existing.get("N8N_WEBHOOK_URL", "http://localhost:5678/webhook"),
        ),
        "SERVER_PORT": ask(
            "FastAPI server port",
            default=existing.get("SERVER_PORT", "8100"),
        ),
        "DEBUG": ask(
            "Debug mode (true/false)",
            default=existing.get("DEBUG", "false"),
        ),
    }

    # Write .env
    lines = ["# Prospector environment — generated by init script", ""]
    for key, val in keys.items():
        lines.append(f"{key}={val}")

    env_path.write_text("\n".join(lines) + "\n")
    success(f".env written ({sum(1 for v in keys.values() if v)} keys configured)")

    # Warn about missing critical keys
    if not keys.get("NOTION_DATABASE_ID"):
        warn("Notion database ID not set — see Step 5 to create the database first")

    return keys


def step_4_personal_info():
    """Collect personal information and write answers.yaml."""
    step(4, "Personal Information")

    answers_path = CONFIG_DIR / "answers.yaml"

    if answers_path.exists():
        # Check if it's been customized (not template defaults)
        content = answers_path.read_text()
        if "Your Name" not in content and "you@example.com" not in content:
            info("answers.yaml already configured")
            if not ask_yes_no("Reconfigure personal info?", default=False):
                return

    print()
    info("This information is used to auto-fill job applications.\n")

    # Personal
    full_name = ask("Full name", required=True)
    email = ask("Email address", required=True)
    phone = ask("Phone number (with country code)", default="")
    linkedin_url = ask("LinkedIn profile URL", default="")
    github_url = ask("GitHub profile URL", default="")
    portfolio_url = ask("Portfolio/website URL", default="")

    print()

    # Work
    years_exp = ask("Years of experience", default="9")
    current_company = ask("Current company", default="")
    availability = ask("Notice period / availability", default="30 days")
    salary = ask("Salary expectation (USD)", default="7000-9000/month")
    work_auth = ask("Work authorization", default="")
    stack_raw = ask("Preferred tech stack (comma-separated)", default="Java, Spring Boot, React, TypeScript, AWS")
    preferred_stack = [s.strip() for s in stack_raw.split(",") if s.strip()]

    print()

    # Answers
    relocate = ask_yes_no("Willing to relocate?", default=True)
    remote = ask_yes_no("Open to remote?", default=True)
    visa = ask_yes_no("Requires visa sponsorship?", default=False)

    print()
    info("Enter a short default cover letter intro (press Enter twice to finish):")
    cover_lines: list[str] = []
    while True:
        line = input("  ")
        if not line and cover_lines:
            break
        cover_lines.append(line)
    cover_letter = "\n".join(cover_lines) if cover_lines else f"I am a senior software engineer with {years_exp} years of experience..."

    # Build YAML manually to preserve formatting
    stack_yaml = "\n".join(f"    - {s}" for s in preferred_stack)

    yaml_content = f"""personal:
  full_name: "{full_name}"
  email: "{email}"
  phone: "{phone}"
  linkedin_url: "{linkedin_url}"
  github_url: "{github_url}"
  portfolio_url: "{portfolio_url}"

work:
  years_experience: {years_exp}
  current_company: "{current_company}"
  availability: "{availability}"
  salary_expectation_usd: "{salary}"
  work_authorization: "{work_auth}"
  preferred_stack:
{stack_yaml}

answers:
  willing_to_relocate: {str(relocate).lower()}
  open_to_remote: {str(remote).lower()}
  requires_visa_sponsorship: {str(visa).lower()}
  cover_letter_default: |
    {cover_letter}
"""
    answers_path.write_text(yaml_content)
    success("config/answers.yaml written")


def step_5_search_config():
    """Configure search parameters."""
    step(5, "Search Configuration")

    config_path = CONFIG_DIR / "config.yaml"

    if config_path.exists():
        content = config_path.read_text()
        if ask_yes_no("config.yaml exists. Reconfigure search parameters?", default=False) is False:
            return

    print()
    titles = ask_list(
        "Job titles to search (comma-separated)",
        default=["Senior Java Developer", "Senior Full Stack Engineer", "Backend Engineer"],
    )
    locations = ask_list(
        "Locations (comma-separated)",
        default=["Remote", "Europe"],
    )
    experience = ask("Experience level", default="senior")

    print()
    info("Rate limits:")
    easy_apply = ask("Max Easy Apply per day", default="25")
    outreach = ask("Max outreach emails per day", default="8")
    claude_calls = ask("Max Claude API calls per day", default="200")

    print()
    info("Schedule (cron format):")
    jobspy_cron = ask("JobSpy scraper schedule", default="0 8 * * *")
    easy_apply_cron = ask("Easy Apply schedule", default="0 9 * * *")
    post_cron = ask("Post scraper schedule", default="0 10 * * *")

    n8n_url = ask("n8n webhook base URL", default="http://localhost:5678/webhook")
    port = ask("FastAPI server port", default="8100")

    # Build YAML
    titles_yaml = "\n".join(f'    - "{t}"' for t in titles)
    locations_yaml = "\n".join(f'    - "{l}"' for l in locations)

    yaml_content = f"""search:
  titles:
{titles_yaml}
  locations:
{locations_yaml}
  experience_level: "{experience}"

limits:
  easy_apply_daily: {easy_apply}
  post_outreach_daily: {outreach}
  claude_calls_daily: {claude_calls}
  post_max_age_hours: 48
  hunter_min_confidence: 70

schedule:
  jobspy_cron: "{jobspy_cron}"
  easy_apply_cron: "{easy_apply_cron}"
  post_scraper_cron: "{post_cron}"

n8n_webhook_url: "{n8n_url}"
server_port: {port}
"""
    config_path.write_text(yaml_content)
    success("config/config.yaml written")


def step_6_blacklist():
    """Configure company blacklist."""
    step(6, "Company Blacklist")

    blacklist_path = CONFIG_DIR / "blacklist.yaml"

    companies = ask_list(
        "Companies to skip (comma-separated, or press Enter for none)",
        default=[],
    )

    if companies:
        companies_yaml = "\n".join(f'  - "{c}"' for c in companies)
        blacklist_path.write_text(f"companies:\n{companies_yaml}\n")
        success(f"config/blacklist.yaml written ({len(companies)} companies)")
    else:
        blacklist_path.write_text("companies:\n  # - \"Company Name\"\n")
        success("config/blacklist.yaml written (empty)")


def step_7_resume():
    """Set up resume files."""
    step(7, "Resume Files")

    pdf_path = ASSETS_DIR / "resume.pdf"
    json_path = ASSETS_DIR / "resume.json"

    # Resume PDF
    if pdf_path.exists():
        success("assets/resume.pdf already exists")
    else:
        print()
        info("Your resume PDF is needed for ATS uploads and email attachments.")
        source = ask("Path to your resume.pdf (or press Enter to skip)")
        if source and Path(source).expanduser().exists():
            shutil.copy2(Path(source).expanduser(), pdf_path)
            success("assets/resume.pdf copied")
        elif source:
            error(f"File not found: {source}")
            warn("Copy your resume.pdf to assets/ manually")
        else:
            warn("Skipped — copy your resume.pdf to assets/ before running ATS automation")

    # Resume JSON
    if json_path.exists():
        success("assets/resume.json already exists")
    else:
        print()
        if ask_yes_no("Generate a resume.json template from your answers.yaml?"):
            _generate_resume_json(json_path)
            success("assets/resume.json template created — edit it with your full work history")
        else:
            warn("Skipped — create assets/resume.json manually (JSON Resume schema)")


def _generate_resume_json(path: Path):
    """Generate a resume.json template from answers.yaml data."""
    import yaml

    answers_path = CONFIG_DIR / "answers.yaml"
    if not answers_path.exists():
        warn("answers.yaml not found, creating minimal template")
        data = {}
    else:
        with open(answers_path) as f:
            data = yaml.safe_load(f) or {}

    personal = data.get("personal", {})
    work = data.get("work", {})

    resume = {
        "basics": {
            "name": personal.get("full_name", "Your Name"),
            "label": f"Senior Software Engineer ({work.get('years_experience', 'N')} years)",
            "email": personal.get("email", ""),
            "phone": personal.get("phone", ""),
            "url": personal.get("portfolio_url", ""),
            "summary": f"Senior software engineer with {work.get('years_experience', 'N')} years of experience. "
                       f"Preferred stack: {', '.join(work.get('preferred_stack', []))}.",
            "location": {
                "city": "",
                "countryCode": "",
            },
            "profiles": [
                p for p in [
                    {"network": "LinkedIn", "url": personal.get("linkedin_url", "")} if personal.get("linkedin_url") else None,
                    {"network": "GitHub", "url": personal.get("github_url", "")} if personal.get("github_url") else None,
                ] if p
            ],
        },
        "work": [
            {
                "name": work.get("current_company", "Current Company"),
                "position": "Senior Software Engineer",
                "startDate": "YYYY-MM",
                "summary": "Describe your role and achievements here.",
                "highlights": [
                    "Add key achievements",
                    "Quantify impact where possible",
                ],
            }
        ],
        "skills": [
            {"name": skill, "level": "Advanced"}
            for skill in work.get("preferred_stack", ["Java", "Spring Boot", "React"])
        ],
        "education": [
            {
                "institution": "Your University",
                "area": "Computer Science",
                "studyType": "Bachelor",
                "startDate": "YYYY",
                "endDate": "YYYY",
            }
        ],
    }

    path.write_text(json.dumps(resume, indent=2, ensure_ascii=False) + "\n")


def step_8_notion_setup(env_keys: dict):
    """Create the Notion database automatically or guide through manual setup."""
    step(8, "Notion Database Setup")

    db_id = env_keys.get("NOTION_DATABASE_ID", "")
    notion_token = env_keys.get("NOTION_TOKEN", "")

    if db_id and len(db_id) > 10:
        success(f"Notion database ID is configured: {db_id[:8]}...")
        if not ask_yes_no("Reconfigure Notion database?", default=False):
            return

    if not notion_token:
        warn("NOTION_TOKEN not set — skipping database creation")
        info("Set your Notion token in .env and run: python scripts/setup_notion_db.py")
        return

    print()
    info("This will create the 'Job Applications' database in your Notion workspace.")
    info("Make sure your Notion integration has access to the target workspace.")
    print()

    if ask_yes_no("Create Notion database automatically?"):
        parent_id = ask("Parent page ID (press Enter to auto-detect or create one)", default="")
        cmd_parts = [sys.executable, str(PROJECT_DIR / "scripts" / "setup_notion_db.py")]
        if parent_id:
            cmd_parts.extend(["--parent-page-id", parent_id])

        info("Running Notion database setup script...")
        print()
        result = subprocess.run(cmd_parts, cwd=str(PROJECT_DIR))

        if result.returncode == 0:
            # Re-read .env to pick up the new database ID
            env_path = PROJECT_DIR / ".env"
            if env_path.exists():
                for line in env_path.read_text().splitlines():
                    if line.startswith("NOTION_DATABASE_ID="):
                        env_keys["NOTION_DATABASE_ID"] = line.split("=", 1)[1].strip()
        else:
            error("Notion setup script failed")
            info("You can retry manually: python scripts/setup_notion_db.py")
    else:
        info("You can create the database manually or run later:")
        info("  python scripts/setup_notion_db.py")
        print()
        new_id = ask("Or paste an existing Notion database ID (press Enter to skip)")
        if new_id:
            _update_env_key("NOTION_DATABASE_ID", new_id)
            env_keys["NOTION_DATABASE_ID"] = new_id
            success("Database ID saved to .env")


def step_9_discord_guide():
    """Guide user through Discord webhook setup."""
    step(9, "Discord Notifications")

    env_path = PROJECT_DIR / ".env"
    content = env_path.read_text() if env_path.exists() else ""

    if "discord.com/api/webhooks/" in content:
        success("Discord webhook is configured")
        return

    if not ask_yes_no("Set up Discord notifications?"):
        warn("Skipped — you can add DISCORD_WEBHOOK_URL to .env later")
        return

    print(f"""
  {BOLD}Create a Discord webhook:{RESET}

  1. Open Discord → Server Settings → Integrations → Webhooks
  2. Click "New Webhook"
  3. Choose a channel (e.g. #job-search)
  4. Copy the webhook URL
""")

    webhook = ask("Paste Discord webhook URL")
    if webhook:
        if "DISCORD_WEBHOOK_URL=" in content:
            lines = content.splitlines()
            lines = [
                f"DISCORD_WEBHOOK_URL={webhook}" if l.startswith("DISCORD_WEBHOOK_URL=") else l
                for l in lines
            ]
            env_path.write_text("\n".join(lines) + "\n")
        else:
            with open(env_path, "a") as f:
                f.write(f"DISCORD_WEBHOOK_URL={webhook}\n")
        success("Discord webhook saved to .env")


def step_10_validate():
    """Validate configuration and test connections."""
    step(10, "Validation")

    errors_found = False

    # Check .env exists
    env_path = PROJECT_DIR / ".env"
    if env_path.exists():
        success(".env file exists")
    else:
        error(".env file missing")
        errors_found = True

    # Check config files
    for name in ["config.yaml", "answers.yaml", "blacklist.yaml"]:
        path = CONFIG_DIR / name
        if path.exists():
            success(f"config/{name} exists")
        else:
            error(f"config/{name} missing")
            errors_found = True

    # Check resume files
    pdf_path = ASSETS_DIR / "resume.pdf"
    json_path = ASSETS_DIR / "resume.json"
    if pdf_path.exists():
        success(f"assets/resume.pdf exists ({pdf_path.stat().st_size / 1024:.0f} KB)")
    else:
        warn("assets/resume.pdf missing — needed for ATS automation and outreach")

    if json_path.exists():
        success(f"assets/resume.json exists ({json_path.stat().st_size / 1024:.0f} KB)")
    else:
        warn("assets/resume.json missing — needed for Claude-generated summaries")

    # Try loading config
    print()
    info("Testing config loader...")
    try:
        sys.path.insert(0, str(PROJECT_DIR))
        from dotenv import load_dotenv
        load_dotenv(PROJECT_DIR / ".env")

        from common.config import load_config, load_answers, load_blacklist, reset
        reset()

        config = load_config()
        success(f"config.yaml loaded — {len(config.search.titles)} titles, {len(config.search.locations)} locations")

        answers = load_answers()
        success(f"answers.yaml loaded — {answers.personal.full_name}")

        blacklist = load_blacklist()
        success(f"blacklist.yaml loaded — {len(blacklist.companies)} companies blocked")

    except Exception as e:
        error(f"Config loading failed: {e}")
        errors_found = True

    # Test Notion connection
    notion_token = os.getenv("NOTION_TOKEN", "")
    notion_db = os.getenv("NOTION_DATABASE_ID", "")
    if notion_token and notion_db:
        info("Testing Notion connection...")
        try:
            import httpx
            resp = httpx.get(
                f"https://api.notion.com/v1/databases/{notion_db}",
                headers={
                    "Authorization": f"Bearer {notion_token}",
                    "Notion-Version": "2022-06-28",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                db_title = resp.json().get("title", [{}])[0].get("plain_text", "Untitled")
                success(f"Notion connected — database: \"{db_title}\"")
            else:
                error(f"Notion API returned {resp.status_code}: {resp.json().get('message', '')}")
                errors_found = True
        except Exception as e:
            error(f"Notion connection failed: {e}")
            errors_found = True
    else:
        warn("Notion not configured — skipping connection test")

    # Test Discord webhook
    discord_url = os.getenv("DISCORD_WEBHOOK_URL", "")
    if discord_url:
        info("Testing Discord webhook...")
        try:
            import httpx
            # Use GET to validate the webhook without sending a message
            resp = httpx.get(discord_url, timeout=10)
            if resp.status_code == 200:
                hook_name = resp.json().get("name", "Unknown")
                success(f"Discord webhook valid — name: \"{hook_name}\"")
            else:
                warn(f"Discord webhook returned {resp.status_code}")
        except Exception as e:
            warn(f"Discord webhook test failed: {e}")
    else:
        warn("Discord webhook not configured — skipping test")

    # Test Anthropic API key
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if anthropic_key and anthropic_key.startswith("sk-ant-"):
        success("Anthropic API key format looks valid")
    elif anthropic_key:
        warn("Anthropic API key set but format looks unusual")
    else:
        warn("Anthropic API key not set — Claude features will not work")

    return not errors_found


def step_11_cron():
    """Offer to set up cron jobs."""
    step(11, "Scheduled Tasks (cron)")

    if not ask_yes_no("Set up cron jobs for daily automation?", default=False):
        warn("Skipped — see docs/getting_started.md for manual cron setup")
        return

    venv_python = PROJECT_DIR / ".venv" / "bin" / "python"
    if not venv_python.exists():
        venv_python = PROJECT_DIR / ".venv" / "Scripts" / "python"

    cron_lines = [
        f"# Prospector — automated job search pipeline",
        f"# JobSpy scraper — 8:00 AM daily",
        f"0 8 * * * cd {PROJECT_DIR} && {venv_python} -m scrapers.jobspy_scraper >> {LOGS_DIR}/cron.log 2>&1",
        f"# AIHawk Easy Apply — 9:00 AM weekdays",
        f"0 9 * * 1-5 {PROJECT_DIR}/scripts/aihawk_wrapper.sh >> {LOGS_DIR}/cron.log 2>&1",
        f"# LinkedIn post scraper — 10:00 AM daily",
        f"0 10 * * * cd {PROJECT_DIR} && {venv_python} -m scrapers.linkedin_posts >> {LOGS_DIR}/cron.log 2>&1",
        f"# Weekly summary — Sunday 6:00 PM",
        f"0 18 * * 0 cd {PROJECT_DIR} && {venv_python} scripts/weekly_summary.py >> {LOGS_DIR}/cron.log 2>&1",
        f"# Export n8n workflows — Sunday midnight",
        f"0 0 * * 0 {PROJECT_DIR}/scripts/export_n8n_workflows.sh >> {LOGS_DIR}/cron.log 2>&1",
    ]

    cron_block = "\n".join(cron_lines)

    print(f"\n{DIM}  The following cron entries will be added:\n")
    for line in cron_lines:
        print(f"  {line}")
    print(f"{RESET}")

    if ask_yes_no("Add these to your crontab?"):
        try:
            # Get existing crontab
            result = run("crontab -l", check=False, capture=True)
            existing = result.stdout if result.returncode == 0 else ""

            if "Prospector" in existing:
                warn("Prospector cron entries already exist — skipping to avoid duplicates")
                return

            new_crontab = existing.rstrip() + "\n\n" + cron_block + "\n"
            proc = subprocess.run(
                "crontab -", shell=True, input=new_crontab,
                text=True, capture_output=True,
            )
            if proc.returncode == 0:
                success("Cron jobs installed")
            else:
                error(f"Failed to install cron: {proc.stderr}")
        except Exception as e:
            error(f"Cron setup failed: {e}")
            info("Add the entries manually with: crontab -e")
    else:
        info("Copy the entries above into your crontab manually: crontab -e")


def step_12_summary():
    """Print final summary and next steps."""
    step(12, "Setup Complete")

    print(f"""
  {GREEN}{BOLD}Prospector is configured!{RESET}

  {BOLD}Quick commands:{RESET}

    {CYAN}# Activate virtual environment{RESET}
    source .venv/bin/activate

    {CYAN}# Test the scraper (no side effects){RESET}
    python -m scrapers.jobspy_scraper --dry-run

    {CYAN}# Start the FastAPI server{RESET}
    python -m orchestration.server

    {CYAN}# Test ATS automation (visible browser){RESET}
    DEBUG=true python -m ats.greenhouse --url "https://boards.greenhouse.io/..."

    {CYAN}# Generate a cold email preview{RESET}
    python -m outreach.email_generator --author "Name" --company "Co" --post-content "..." --dry-run

  {BOLD}Still needed:{RESET}

    {DIM}•{RESET} Set up n8n workflows (see docs/getting_started.md, Step 9)
    {DIM}•{RESET} Set up AIHawk (see docs/aihawk_setup.md)
    {DIM}•{RESET} Export LinkedIn cookies for post scraping (see docs/getting_started.md, Step 8)
    {DIM}•{RESET} Review and edit assets/resume.json with your full work history

  {BOLD}Documentation:{RESET}

    {DIM}•{RESET} docs/getting_started.md  — Full setup walkthrough
    {DIM}•{RESET} docs/aihawk_setup.md     — AIHawk integration guide
    {DIM}•{RESET} README.md                — Architecture overview
""")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    banner()

    print(f"  {DIM}This wizard will walk you through setting up Prospector.")
    print(f"  Press Ctrl+C at any time to exit. Progress is saved as you go.{RESET}")

    try:
        step_1_directories()
        step_2_venv()
        env_keys = step_3_api_keys()
        step_4_personal_info()
        step_5_search_config()
        step_6_blacklist()
        step_7_resume()
        step_8_notion_setup(env_keys)
        step_9_discord_guide()
        valid = step_10_validate()
        step_11_cron()
        step_12_summary()

        if not valid:
            print(f"  {YELLOW}⚠ Some validation checks failed — review the warnings above.{RESET}\n")

    except KeyboardInterrupt:
        print(f"\n\n  {YELLOW}Setup interrupted. Run again to continue where you left off.{RESET}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
