# AI News Agent

A smart Python agent that runs daily to fetch AI-related news, summarizes articles using GPT-4o-mini, ranks the most important stories, and outputs the top 10 AI updates of the day. Also sends a notification to an iPhone using Pushover with the Notion URL which takes the user directly to the Notion page with the top 10 AI articles of the day.

## Features

- **Multi-source news aggregation**: Fetches from arXiv, Hacker News, TechCrunch, and more
- **AI-powered summarization**: Uses GPT-4o-mini to create concise 2-3 sentence summaries
- **Intelligent ranking**: GPT-4o-mini ranks articles by importance for AI researchers, builders, and investors
- **Multiple output formats**: Markdown files, Notion pages, and email delivery
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

Create and edit `.env` with your API keys:

```env
# Required: OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_ORGANIZATION_ID=your_openai_organization_id_here
OPENAI_PROJECT_ID=your_openai_project_id_here

# Optional: Notion Integration
NOTION_TOKEN=your_notion_token_here
NOTION_DATABASE_ID=your_notion_database_id_here

# Optional: Pushover Configuration (iPhone notifications)
PUSHOVER_TOKEN=your_app_token_here
PUSHOVER_USER=your_user_key_here

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
# Run once for today's news
python ai_news_agent.py

# Run for a specific date
python ai_news_agent.py --date 2025-01-15

# Run with debug logging
python ai_news_agent.py --debug

# Run scheduled daily at 9 AM
python ai_news_agent.py --schedule
```

## Usage Examples

### Basic Usage

```bash
# Generate today's AI news summary
python ai_news_agent.py
```

This will:
1. Fetch AI-related articles from multiple sources
2. Summarize each article using GPT-4o-mini
3. Rank and select the top 10 most important stories
4. Save the results to `top_ai_news_YYYY-MM-DD.md`

### Advanced Usage

```bash
# Generate news for a specific date
python ai_news_agent.py --date 2025-01-15

# Output to Notion (requires Notion API setup)
python ai_news_agent.py --output notion

# Send via email (requires email configuration)
python ai_news_agent.py --output email

# Enable debug logging
python ai_news_agent.py --debug

# Run scheduled daily
python ai_news_agent.py --schedule
```

## Output Formats

### Markdown Output

The default output creates a markdown file with the following structure:

```markdown
# Top AI News - 2025-01-15

Generated on: 2025-01-15 14:30:00

## Top 10 AI Updates of the Day

### 1. [Article Title]

**Source:** [Source Name]

**Summary:** [GPT-4o-mini generated 2-3 sentence summary]

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

The agent currently fetches from:

- arXiv AI & ML papers (latest research)
- Hacker News AI discussions
- TechCrunch AI news
- NVIDIA Blog (GPU/AI content)
- Hugging Face Blog (ML tools)
- OpenAI Blog (latest updates)
- Google Research (AI research)
- Meta Research (filtered AI content)
- AI News dedicated sites

Additional sources can be easily added by extending the `sources` configuration in the `AINewsAgent` class.

## Architecture

### Core Components

- **`AINewsAgent`**: Main class handling the entire pipeline
- **`Article`**: Data class representing news articles
- **`NotionClient`**: Handles Notion API integration
- **`EmailClient`**: Handles email delivery

### Pipeline Flow

1. **Article Collection**: Fetches articles from multiple sources
2. **Content Filtering**: Filters for AI-related content
3. **Summarization**: Uses GPT-4o-mini to create concise summaries
4. **Ranking**: Uses GPT-4o-mini to rank articles by importance
5. **Output Generation**: Creates formatted output in various formats

### GPT-4o-mini Prompts

The agent uses carefully crafted prompts for:

- **Summarization**: Creates 2-3 sentence summaries focusing on technical developments and business implications
- **Ranking**: Selects the most important articles based on technical significance, business impact, and research value

## Cost Comparison

### OpenAI API

- GPT-4o-mini: ~$0.00015 per 1K tokens (Currenty used model and very affordable)
- GPT-4o: ~$0.005 per 1K tokens (33x more expensive)
- GPT-4: ~$0.03 per 1K tokens (200x more expensive)
- GPT-3.5-turbo: ~$0.0005 per 1K tokens (Though 3x more expensive than 4o-mini)

### Model Options Available

If you want to upgrade for better quality, one could switch to:
- GPT-4o-mini - Current choice, good balance
- GPT-4o - Better reasoning, more expensive
- GPR-4 - Excellent reasoning, very capable

### Anthropic (Claude) - Optional

- Claude 3.5 Sonnet: ~$0.003 per 1K tokens (20x more expensive than 4o-mini)
- Claude 3.5 Haiku: ~$0.00025 per 1K tokens (1.7x more expensive than 4o-mini)
- Claude 3 Opus: ~$0.015 per 1K tokens (100x more expensive than 4o-mini)

### Google (Gemini) - Optional

- Gemini 1.5 Pro: ~$0.00375 per 1K tokens (25x more expensive than 4o-mini)
- Gemini 1.5 Flash: ~$0.000075 per 1K tokens (2x cheaper than 4o-mini!)

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for GPT-4o-mini access |
| `OPENAI_ORGANIZATION_ID` | Yes | OpenAI Organization ID for GPT-4o-mini access |
| `OPENAI_PROJECT_ID` | Yes | OpenAI Project ID for GPT-4o-mini access |
| `NOTION_TOKEN` | Yes | Notion integration token |
| `NOTION_DATABASE_ID` | Yes | Notion database ID |
| `PUSHOVER_TOKEN` | No | Pushover integration app token |
| `PUSHOVER_USERD` | No | Pushover user key |
| `SMTP_SERVER` | No | SMTP server for email |
| `EMAIL_USER` | No | Email username |
| `EMAIL_PASSWORD` | No | Email password |
| `RECIPIENT_EMAIL` | No | Email recipient |
| `LOG_LEVEL` | No | Logging level (INFO, DEBUG, etc.) |

### Command Line Arguments

| Argument | Description |
|----------|-------------|
| `--date` | Date in YYYY-MM-DD format (default: today) |
| `--output` | Output format: markdown, notion, email |
| `--debug` | Enable debug logging |
| `--schedule` | Run scheduled daily at 9 AM |

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
       
       <key>RunAtLoad</key>
       <false/>
       
       <key>KeepAlive</key>
       <false/>
       
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

Logs are written to both console and `ai_news_agent.log`:

```bash
# View logs
tail -f ai_news_agent.log

# Set log level
export LOG_LEVEL=DEBUG
python ai_news_agent.py
```

## Development

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
- Ensure you have access to GPT-4o-mini

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
