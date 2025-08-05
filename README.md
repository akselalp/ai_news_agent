# AI News Agent

A smart Python agent that runs daily to fetch AI-related news, summarize articles using GPT-4, rank the most important stories, and output the top 10 AI updates of the day.

## Features

- **Multi-source news aggregation**: Fetches from arXiv, Hacker News, TechCrunch, and more
- **AI-powered summarization**: Uses GPT-4 to create concise 2-3 sentence summaries
- **Intelligent ranking**: GPT-4 ranks articles by importance for AI researchers, builders, and investors
- **Multiple output formats**: Markdown files, Notion pages, and email delivery
- **Scheduled execution**: Can run daily automatically
- **Comprehensive logging**: Detailed logs for monitoring and debugging
- **Error handling**: Robust error handling and fallback mechanisms

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd ai_news_agent

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Setup

Copy the example environment file and configure your API keys:

```bash
cp env_example.txt .env
```

Edit `.env` with your API keys:

```env
# Required: OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Notion Integration
NOTION_TOKEN=your_notion_token_here
NOTION_DATABASE_ID=your_notion_database_id_here

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
python ai_news_agent.py --date 2024-01-15

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
2. Summarize each article using GPT-4
3. Rank and select the top 10 most important stories
4. Save the results to `top_ai_news_YYYY-MM-DD.md`

### Advanced Usage

```bash
# Generate news for a specific date
python ai_news_agent.py --date 2024-01-15

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
# Top AI News - 2024-01-15

Generated on: 2024-01-15 14:30:00

## Top 10 AI Updates of the Day

### 1. [Article Title]

**Source:** [Source Name]

**Summary:** [GPT-4 generated 2-3 sentence summary]

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

### Email Integration

To use email delivery:

1. Configure SMTP settings (Gmail recommended)
2. Use an app password for Gmail
3. Set recipient email address
4. Configure environment variables

## News Sources

The agent currently fetches from:

- **arXiv** (cs.AI): Latest AI research papers
- **Hacker News**: AI-related posts and discussions
- **TechCrunch**: AI technology news and startups

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
3. **Summarization**: Uses GPT-4 to create concise summaries
4. **Ranking**: Uses GPT-4 to rank articles by importance
5. **Output Generation**: Creates formatted output in various formats

### GPT-4 Prompts

The agent uses carefully crafted prompts for:

- **Summarization**: Creates 2-3 sentence summaries focusing on technical developments and business implications
- **Ranking**: Selects the most important articles based on technical significance, business impact, and research value

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for GPT-4 access |
| `NOTION_TOKEN` | No | Notion integration token |
| `NOTION_DATABASE_ID` | No | Notion database ID |
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

### Common Issues

**OpenAI API Errors**
- Verify your API key is correct
- Check your OpenAI account has sufficient credits
- Ensure you have access to GPT-4

**Network Errors**
- Check your internet connection
- Verify the news source URLs are accessible
- Check firewall settings

**Notion Integration Issues**
- Verify your integration token is correct
- Ensure the database is shared with your integration
- Check the database has the required properties

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
