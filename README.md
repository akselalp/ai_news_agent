# AI News Agent

A smart Python agent that runs daily to fetch AI-related news, summarizes articles using configurable OpenAI chat models (defaults: `gpt-4o-mini` for summarization and ranking), ranks the most important stories for practitioners, and outputs the top N AI updates (default 10). **Cross-run memory** (default on) stops the same RSS/API items from resurfacing every day. Optional Pushover notification includes the Notion URL when you use `daily_scheduler.py` / `run_agent.py`.

## Features

- **Multi-source news aggregation**: Fetches from arXiv, Hacker News, TechCrunch, and more
- **Cross-run deduplication**: Persistent normalized URLs + headline fingerprints with cooldowns (`seen_articles.py`, default path `data/seen_articles.json`) — by default only **digest placements** (your ranked top N) are recorded after a **successful** output, so RSS staleness does not exhaust the candidate pool; optional `SEEN_RECORD_SCOPE=summarized` restores legacy “remember everything summarized” behavior
- **AI-powered summarization**: Uses OpenAI chat models (`SUMMARY_MODEL` / `RANK_MODEL`, see defaults below); prompts tuned for builders/researchers (specifics over hype)
- **Intelligent ranking**: Model returns strict JSON (`ranked_article_numbers`); regex fallback with loud logging if parsing fails
- **Multiple output formats**: Markdown files, Notion pages, email delivery, and Slack (incoming webhook)
- **Scheduled execution**: Can run daily automatically
- **Scheduled Updates and Notifications**: Updates Notion each day and sends a notification to an Iphone with the Notion page URL using Pushover
- **Comprehensive logging**: Detailed logs for monitoring and debugging
- **Error handling**: Robust error handling and fallback mechanisms

## Quick Start

### 1. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/akselalp/ai_news_agent.git
cd ai_news_agent

# Create virtual environment (recommended)
python3 -m venv ai_news_env
source ai_news_env/bin/activate  # On macOS/Linux
# or
ai_news_env\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Setup

Create `.env` from `.env.example`. Important keys:

```env
# Required: OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Optional: org/project scoping for newer keys
OPENAI_ORGANIZATION_ID=your_openai_organization_id_here
OPENAI_PROJECT_ID=your_openai_project_id_here

# Models (optional — defaults below apply when unset)
SUMMARY_MODEL=gpt-4o-mini
RANK_MODEL=gpt-4o-mini

# Optional caps / tuning
TOP_ARTICLES=10
SUMMARIZE_MAX_ARTICLES=
ARTICLE_DATE_FILTER=false
DATE_FILTER_KEEP_UNKNOWN=true

# Optional: Notion Integration
NOTION_TOKEN=your_notion_token_here
NOTION_DATABASE_ID=your_notion_database_id_here

# Optional: Pushover Configuration (iPhone notifications)
PUSHOVER_TOKEN=your_app_token_here
PUSHOVER_USER=your_user_key_here

# Optional: Slack Configuration (legacy SLACK_WEBHOOK also accepted)
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/XXX/YYY/ZZZ"

# Optional: Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password_here
RECIPIENT_EMAIL=recipient@example.com

# Logging
LOG_LEVEL=INFO
```

### 3. Run the Agent

```bash
# Run once for today's news (Markdown output by default)
python ai_news_agent.py

# Label output with a date (collection still uses live feeds unless you filter)
python ai_news_agent.py --date 2026-05-04

# Fetch + dedupe + filters only — no OpenAI calls (good for debugging sources)
python ai_news_agent.py --dry-run

# Keep only articles whose published timestamp falls on that UTC calendar day
python ai_news_agent.py --date 2026-05-04 --filter-by-date

# Rank/output a different top-N (default 10, or set TOP_ARTICLES in .env)
python ai_news_agent.py --top-n 15

# Run with debug logging
python ai_news_agent.py --debug

# Run scheduled daily at 9 AM (in-process scheduler)
python ai_news_agent.py --schedule
```

**LaunchAgent / cron:** Prefer `run_agent.py` so `.env` loads before `daily_scheduler.py` runs (Notion + optional Slack + Pushover):

```bash
/path/to/venv/bin/python /path/to/ai_news_agent/run_agent.py
```

## Usage Examples

### Basic Usage

```bash
# Generate today's AI news summary
python ai_news_agent.py
```

This will:
1. Fetch AI-related articles from multiple sources
2. Summarize each article using your configured `SUMMARY_MODEL` (default `gpt-4o-mini`)
3. Rank and select the top N stories (`TOP_ARTICLES` / `--top-n`, default 10)
4. Save the results to `top_ai_news_YYYY-MM-DD.md`

### Advanced Usage

```bash
# Generate news for a specific date
python ai_news_agent.py --date 2025-08-30

# Output to Notion (requires Notion API setup)
python ai_news_agent.py --output notion

# Send via email (requires email configuration)
python ai_news_agent.py --output email

# Post to Slack (requires SLACK_WEBHOOK_URL)
python ai_news_agent.py --output slack

# Enable debug logging
python ai_news_agent.py --debug

# Run scheduled daily
python ai_news_agent.py --schedule
```

## Output Formats

### Markdown Output

The default output creates a markdown file with the following structure:

```markdown
# Top AI News - 2025-08-30

Generated on: 2025-08-30 09:00:00

## Top 10 AI Updates of the Day

### 1. [Article Title]

**Source:** [Source Name]

**Summary:** [Model-generated 2–3 sentence summary]

**Link:** [Article URL]

---
```

### Notion Integration

To use Notion integration:

1. Create a Notion integration at https://www.notion.so/my-integrations
2. Get your integration token
3. Create a database in Notion with "Title" and "Date" properties
4. Share the database with your integration
5. Get the database ID from the URL
6. Configure the environment variables

### Pushover Integration

To use Pushover integration:

1. Create a Pushover account at https://pushover.net/app
2. Get your Pushover User Key form the main page
3. Create the app in Pushover to get your App Token, Click "Create an Application" and name it something like "AI News Agent"
4. Add both values to your .env file
5. Install the Python package: pip install pushover-complete
6. Test it with a notification

### Email Integration

To use email delivery:

1. Configure SMTP settings (Gmail recommended)
2. Use an app password for Gmail
3. Set recipient email address
4. Configure environment variables

## News Sources

The agent currently pulls from (RSS/API/scrape mix):

- arXiv AI & ML (`cs.AI`, `cs.LG`)
- Hacker News (Algolia API)
- TechCrunch AI tag
- NVIDIA Blog (RSS + keyword filter)
- Hugging Face blog
- OpenAI blog
- **DeepMind** (official RSS: `deepmind.google/blog/rss.xml`)
- **Google AI blog** (RSS: `blog.google/technology/ai` — replaces brittle Gemini landing-page scraping)
- Anthropic news (HTML scrape — may break if the site changes)
- Mistral news (HTML scrape)
- Artificial Intelligence News site

Additional sources can be added via `AINewsAgent.sources` in `ai_news_agent.py`.

## Cross-run deduplication

RSS feeds often keep the same links at the top for many days, which made older versions of this agent repeat stories. Now:

1. Each article URL is **normalized** (stable host/path, tracking query params stripped).
2. **Headlines are normalized** (strip trailing `| TechCrunch`, `— NVIDIA Blog`, etc.) so syndicated hed lines align for dedupe.
3. **Slug keys** (last meaningful URL path segment) and **core title keys** (long alphanumeric headline prefix) catch the **same story on different URLs** or with minor wording drift — where URL-only dedupe fails.
4. After a successful run (**Markdown** with non-empty output, **Slack/Email** success, or **Notion** page created — tracked via `last_notion_url`), **digest placements** (the ranked top N actually shipped) are written to `SEEN_ARTICLES_PATH` by default (`SEEN_RECORD_SCOPE=digest`). Set `SEEN_RECORD_SCOPE=summarized` if you want every summarized row remembered instead (can shrink your candidate pool quickly when feeds repeat the same URLs).
5. Items inside cooldown windows are skipped before summarization (defaults **~120d URL**, **~90d title**, with slug/core aligned unless overridden — see Configuration table).
6. Store rows are **pruned only after long retention** (default ~548 days) so stories don’t reappear simply because history was trimmed.
7. Within each day, candidates are **sorted newest-first** when publish dates parse.

If Notion posting fails, the seen-store is **not** updated (you shouldn’t “consume” stories that didn’t ship). Watch logs for `Recorded … → seen store`; recurring duplicates plus missing log lines often mean outputs failed silently earlier.

After upgrading dedupe logic, or if you previously ran with “summarize-all” recording and now see **every candidate skipped**, **delete `data/seen_articles.json` once** for a clean slate.

Disable with `CROSS_RUN_DEDUPE=false` if you want the legacy “feeds only” behavior.

### If the digest repeats the same #1 / same URLs for days

1. **Confirm the seen store updates**: After each successful Notion run you should see `Recorded N articles → seen store` in `ai_news_agent.log` with the **same absolute path** every time. If that line is missing, digest URLs were not persisted — often because Notion did not return a page URL (now mitigated with an id-based fallback in `utils.py`) or `CROSS_RUN_DEDUPE=false`.
2. **One store file**: Older setups used `SEEN_ARTICLES_PATH=data/seen_articles.json` resolved from the **process working directory**, so a cron job started from `$HOME` could write a different file than `run_agent.py` (which `cd`s into the repo). Relative paths are now anchored to the repo root; **merge or delete stray copies** under `~/data/` if you had them.
3. **Ranking fallback**: If logs often show `Ranking fallback` / `fallback_first_n`, the model output isn’t parsing and the digest defaults to “first N summaries” (feed order). Fix ranking or parsing first — dedupe alone won’t rotate stories.
4. **Same story, different URLs and different headlines** (e.g. shortened titles): URL/title/slug keys may all miss. Lower cooldowns only mask the issue; tightening sources or adding manual blocks is the robust fix.

### Faster collection & richer summaries

- **`FETCH_PARALLEL`** (default `true`) pulls sources concurrently with isolated HTTP sessions (safer than sharing one `Session` across threads). Set `FETCH_PARALLEL=false` if a provider rate-limits you.
- **`ENRICH_ARTICLE_HTML=true`** optionally performs a **bounded** GET on article URLs when the RSS/snippet text is short, improving summaries without changing the rest of the pipeline. Tune **`ENRICH_MAX_PER_RUN`** to control extra traffic.
- **`--dry-run`** runs collection + dedupe + filters only — useful for validating sources and cross-run memory without spending tokens.

## Architecture

### Core Components

- **`AINewsAgent`**: Main class handling the entire pipeline
- **`Article`**: Data class representing news articles
- **`NotionClient` / `EmailClient` / `SlackClient`**: Output integrations (`utils.py`)
- **`SeenArticlesStore`** (`seen_articles.py`): Cross-run memory (URLs, titles, slugs, core title keys)

### Pipeline Flow

1. **Article Collection**: Fetches articles from multiple sources
2. **Dedupe**: Normalized URL + slug + title fingerprint + core title key (within run)
3. **Optional date filter**: UTC calendar day when enabled
4. **Recency sort**: Newest publish date first when parseable
5. **Cross-run filter**: Drop items matching URL/slug/title/core still on cooldown
6. **Summarization**: Calls OpenAI chat completions (`SUMMARY_MODEL`)
7. **Ranking**: Structured JSON via `RANK_MODEL`, with regex fallback
8. **Output**: Markdown / Notion / email / Slack, then **persist seen store** (digest placements by default) if output succeeded

### Prompt design

The agent uses carefully crafted prompts for:

- **Summarization**: Creates 2-3 sentence summaries focusing on technical developments and business implications
- **Ranking**: Selects the most important articles based on technical significance, business impact, and research value (structured JSON where supported)

## Cost Comparison

### OpenAI API

Pricing changes frequently — see [OpenAI Pricing](https://openai.com/pricing). Defaults (`gpt-4o-mini`) favor low cost; upgrade `SUMMARY_MODEL` / `RANK_MODEL` if you want stronger reasoning.

### Local usage logging

There is **no** standalone billing API wired into this repo. `cost_monitor.py` prints dashboard links and reminds you that each run logs token usage lines to `ai_news_agent.log` (`OpenAI usage [...]` and end-of-run totals).

### Anthropic (Claude) - Optional

- Claude 3.5 Sonnet: ~$0.003 per 1K tokens (60x more expensive than 5-nano)
- Claude 3.5 Haiku: ~$0.00025 per 1K tokens (5.1x more expensive than 5-nano)
- Claude 3 Opus: ~$0.015 per 1K tokens (300x more expensive than 5-nano)

### Google (Gemini) - Optional

- Gemini 1.5 Pro: ~$0.00375 per 1K tokens (75x more expensive than 5-nano)
- Gemini 1.5 Flash: ~$0.000075 per 1K tokens (1.5x cheaper than 5-nano!)

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `OPENAI_ORGANIZATION_ID` | No | Organization ID (only if your key requires it) |
| `OPENAI_PROJECT_ID` | No | Project ID (only if your key requires it) |
| `SUMMARY_MODEL` | No | Chat model for summaries (default `gpt-4o-mini`) |
| `RANK_MODEL` | No | Chat model for ranking JSON (default `gpt-4o-mini`) |
| `TOP_ARTICLES` | No | Default top‑N to rank/output (CLI `--top-n` overrides) |
| `SUMMARIZE_MAX_ARTICLES` | No | Hard cap on how many collected articles are summarized (cost guardrail) |
| `ARTICLE_DATE_FILTER` | No | If `true`, `daily_scheduler` / CLI `--filter-by-date` restrict to UTC publication day |
| `DATE_FILTER_KEEP_UNKNOWN` | No | When date filtering is on, keep items with unknown dates (default `true`) |
| `NOTION_TOKEN` | For Notion output | Integration token |
| `NOTION_DATABASE_ID` | For Notion output | Parent database ID |
| `PUSHOVER_TOKEN` | No | Pushover application token |
| `PUSHOVER_USER` | No | Pushover user key (`PUSHOVER_USER_KEY` alias supported) |
| `SLACK_WEBHOOK_URL` | No | Incoming webhook URL (`SLACK_WEBHOOK` legacy alias supported) |
| `SMTP_SERVER` | For email | SMTP hostname |
| `EMAIL_USER` | For email | SMTP username |
| `EMAIL_PASSWORD` | For email | SMTP password / app password |
| `RECIPIENT_EMAIL` | For email | Recipient |
| `CROSS_RUN_DEDUPE` | No | `true`/`false` — persistent dedupe across runs (default `true`) |
| `SEEN_ARTICLES_PATH` | No | JSON store path (default `data/seen_articles.json`). **Relative paths are resolved from the repo root** (the directory that contains `seen_articles.py`), not from the shell’s current working directory — so LaunchAgent and manual runs share one file. Use an absolute path only if you intentionally want another location. |
| `SEEN_RECORD_SCOPE` | No | `digest` (default): remember ranked top N only; `summarized`: remember every summarized article (legacy; shrinks pool faster) |
| `URL_COOLDOWN_DAYS` | No | Skip same normalized URL for N days after last successful digest (default **120**) |
| `TITLE_COOLDOWN_DAYS` | No | Skip same normalized headline for N days (default **90**) |
| `SLUG_COOLDOWN_DAYS` | No | Skip same URL path slug (mirrored stories); default **same as URL cooldown** |
| `CORE_TITLE_COOLDOWN_DAYS` | No | Skip same “core” headline prefix across wording drift; default **same as title cooldown** |
| `SEEN_STORE_RETENTION_DAYS` | No | Prune store entries older than this (default **548** ~18mo) |
| `LOG_LEVEL` | No | Logging level (INFO, DEBUG, etc.) |
| `LOG_FILE_PATH` | No | Log file path (default `ai_news_agent.log`) |
| `LOG_FILE_MAX_BYTES` | No | Rotate after this size (default ~10 MiB) |
| `LOG_FILE_BACKUP_COUNT` | No | Rotating backups to keep (default 5) |
| `LOG_DISABLE_ROTATE` | No | Set `true` to use a single growing log file |
| `FETCH_PARALLEL` | No | Fetch sources concurrently (default `true`; set `false` if rate-limited) |
| `FETCH_MAX_WORKERS` | No | Thread pool size when parallel fetch is on (default `8`) |
| `ENRICH_ARTICLE_HTML` | No | `true` to fetch article HTML when excerpts are thin (default off; costs extra HTTP) |
| `ENRICH_MAX_PER_RUN` | No | Cap HTML fetches per pipeline run (default `12`) |
| `ENRICH_MIN_PLAINTEXT_CHARS` | No | Fetch HTML when excerpt shorter than this (default `360`) |
| `ENRICH_MAX_PLAINTEXT_CHARS` | No | Max stored plaintext from HTML (default `12000`) |
| `ENRICH_MAX_RESPONSE_BYTES` | No | Skip responses larger than this (default `800000`) |

### Command Line Arguments

| Argument | Description |
|----------|-------------|
| `--date` | Label outputs; optional companion to `--filter-by-date` / `ARTICLE_DATE_FILTER` |
| `--output` | `markdown`, `notion`, `email`, or `slack` |
| `--top-n` | Rank/output N articles (overrides `TOP_ARTICLES`) |
| `--filter-by-date` | Keep articles published on `--date` (UTC day; best-effort parsing) |
| `--dry-run` | Collect + filter only; **no** OpenAI, ranking, **or any output** (Notion/Slack/email/file unchanged; seen store not written) |
| `--debug` | Enable debug logging |
| `--schedule` | Run in-process daily at 9:00 |

## Scheduling

### Using the Built-in Scheduler

```bash
python ai_news_agent.py --schedule
```

This runs the agent daily at 9:00 AM.

### Using Cron (Linux/Mac)

Add to your crontab:

```bash
# Edit crontab
crontab -e

# Add this line to run daily at 9 AM
0 9 * * * cd /path/to/ai_news_agent && python ai_news_agent.py
```

### Using Task Scheduler (Windows)

1. Open Task Scheduler
2. Create a new basic task
3. Set trigger to daily at 9:00 AM
4. Set action to start program: `python ai_news_agent.py`
5. Set start in: `/path/to/ai_news_agent`

### Using macOS LaunchAgent (macOS)

For automated daily execution on macOS:

1. **Create LaunchAgent Configuration**
   ```bash
   # Create the plist file
   nano ~/Library/LaunchAgents/com.user.ai-news-agent.plist
   ```

2. **Add This Configuration** (replace paths with your own):
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
   <plist version="1.0">
   <dict>
       <key>Label</key>
       <string>com.user.ai-news-agent</string>
       
       <key>ProgramArguments</key>
       <array>
           <string>/path/to/your/python</string>
           <string>/path/to/ai_news_agent/daily_scheduler.py</string>
       </array>
       
       <key>WorkingDirectory</key>
       <string>/path/to/ai_news_agent</string>
       
       <key>StartCalendarInterval</key>
       <dict>
           <key>Hour</key>
           <integer>9</integer>
           <key>Minute</key>
           <integer>0</integer>
       </dict>
       
       <key>StandardErrorPath</key>
       <string>/path/to/ai_news_agent/scheduler_error.log</string>
       
       <key>StandardOutPath</key>
       <string>/path/to/ai_news_agent/scheduler_output.log</string>
   </dict>
   </plist>
   ```

3. **Load the LaunchAgent**
   ```bash
   launchctl load ~/Library/LaunchAgents/com.user.ai-news-agent.plist
   ```

4. **Verify it's Running**
   ```bash
   launchctl list | grep ai-news
   ```

**Note**: Replace `/path/to/your/python` with your actual Python path (e.g., `/usr/bin/python3` or `/Users/username/anaconda3/envs/venv_name/bin/python3`) and `/path/to/ai_news_agent` with your actual project directory.

**Configuration Options:**
- **Scheduled Execution** (shown above): Runs at exactly 9:00 AM daily using `StartCalendarInterval`
- **Continuous Execution**: Change `RunAtLoad` to `true` and `KeepAlive` to `true` if you want it to run continuously and check every minute

## Error Handling

The agent includes comprehensive error handling:

- **API Rate Limiting**: Automatic delays between API calls
- **Network Failures**: Retry logic for failed requests
- **Missing Content**: Graceful handling of articles without summaries
- **Configuration Errors**: Clear error messages for missing environment variables

## Logging

Logs go to **stderr** and to **`LOG_FILE_PATH`** (default `ai_news_agent.log`). By default the file uses a **rotating handler** (~10 MiB × 5 backups). Set `LOG_DISABLE_ROTATE=true` for a single ever-growing file.

```bash
# View logs
tail -f ai_news_agent.log

# Set log level
export LOG_LEVEL=DEBUG
python ai_news_agent.py
```

## Development

### Tests

```bash
pip install -r requirements-dev.txt
pytest
```

GitHub Actions runs the same suite on push/PR (`.github/workflows/ci.yml`).

### Ideas for a “bulletproof” vNext

Not implemented yet, but high leverage if you keep pushing quality: **embedding-based near-duplicate detection** (beyond URL/title fingerprints), **allowlisted full-text extraction** with per-domain timeouts, **structured telemetry** (success counters per source, latency histograms), **dead-letter / retry queues** for flaky integrations, **secret scanning** in CI, and **golden-file regression tests** on fixture HTML/RSS snapshots.

### SaaS / multi-tenant (future)

This repo is a solid single-user automation. To charge customers later you would typically add: authenticated accounts, **per-tenant `SEEN_ARTICLES_PATH`** (or a database row per subscriber), quotas on `SUMMARIZE_MAX_ARTICLES`, hosted cron/LaunchAgent equivalents, observability (structured logs + alerts), and explicit rate limits on OpenAI. The cross-run store is intentionally path-based so you can scope one file per customer without changing core logic.

### Adding New Sources

To add a new news source:

1. Add source configuration to `self.sources` in `AINewsAgent.__init__()`
2. Implement a parser method (e.g., `_parse_new_source_feed()`)
3. Add the parser to the `_fetch_from_source()` method

### Extending Output Formats

To add a new output format:

1. Add the format to the `--output` choices in `main()`
2. Implement an `_output_newformat()` method
3. Add the format to the `output_results()` method

## Troubleshooting

### Python Environment Issues

**Shebang Line Problems**
If you encounter issues with the shebang line (`#!/usr/bin/env python3`):

1. **For system Python users**: The default shebang should work fine
2. **For virtual environment users**: 
   - Open `ai_news_agent.py`
   - Replace line 1: `#!/usr/bin/env python3` 
   - With: `#!/path/to/your/venv/bin/python3`
   - Example: `#!/Users/username/anaconda3/envs/myenv/bin/python3`

**Virtual Environment Setup**
```bash
# Create virtual environment
python3 -m venv ai_news_env

# Activate it
source ai_news_env/bin/activate  # On macOS/Linux
# or
ai_news_env\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt

# Run the agent
python ai_news_agent.py
```

### Common Issues

**OpenAI API Errors**
- Verify your API key is correct
- Check your OpenAI account has sufficient credits
- Verify your account has access to the chat models set in `SUMMARY_MODEL` / `RANK_MODEL`

**Network Errors**
- Check your internet connection
- Verify the news source URLs are accessible
- Check firewall settings

**Notion Integration Issues**
- Verify your integration token is correct
- Ensure the database is shared with your integration
- Check the database has the required properties

**Pushover Integration Issues**
- Verify your app token working correctly
- Ensure your user key is correct

**Email Delivery Issues**
- Verify SMTP settings
- Use app passwords for Gmail
- Check recipient email address

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Open an issue on GitHub with detailed information
