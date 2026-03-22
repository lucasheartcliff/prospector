# AIHawk Setup Guide

AIHawk is an external open-source bot for LinkedIn Easy Apply automation.

## 1. Clone AIHawk

```bash
git clone https://github.com/AIHawk-FOSS/Auto_Jobs_Applier_AIHawk.git ~/aihawk
cd ~/aihawk
pip install -r requirements.txt
```

## 2. Configure AIHawk

Copy Prospector's `config/answers.yaml` into AIHawk's expected location, or symlink:

```bash
ln -s ~/projects/prospector/config/answers.yaml ~/aihawk/data_folder/plain_text_resume.yaml
```

### Search filters

Edit AIHawk's config to match your `config/config.yaml`:

- **Titles:** Senior Java Developer, Senior Full Stack Engineer, Backend Engineer
- **Locations:** Remote, Europe
- **Experience:** Senior
- **Daily cap:** 25 applications
- **Delay:** 3–8 seconds (randomized)
- **Skip non-Easy Apply:** true

### Claude API integration

Set your Anthropic API key in AIHawk's `.env` or config:

```
LLM_API_KEY=sk-ant-...
```

AIHawk uses Claude to answer novel form questions not covered by `answers.yaml`.

## 3. Create blacklist

Symlink Prospector's blacklist:

```bash
ln -s ~/projects/prospector/config/blacklist.yaml ~/aihawk/data_folder/company_blacklist.yaml
```

## 4. First supervised run

```bash
cd ~/aihawk
DEBUG=true python main.py --max-applications 10
```

Watch the first 10 applications. Check `missed_questions.log` and update `answers.yaml` with any missing answers.

## 5. n8n integration

After each AIHawk run, it can POST a summary to n8n:

- **Webhook URL:** `http://localhost:5678/webhook/easy-apply`
- **Payload:** Array of `{title, company, url, timestamp}`

Configure this in AIHawk's settings or use `scripts/aihawk_wrapper.sh` which handles the POST automatically.

## 6. Production run

```bash
# Via wrapper script (recommended)
./scripts/aihawk_wrapper.sh

# Or via cron
# 0 9 * * * /home/user/projects/prospector/scripts/aihawk_wrapper.sh >> /home/user/projects/prospector/logs/aihawk.log 2>&1
```
