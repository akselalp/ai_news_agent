"""
Utility functions for AI News Agent.

This module contains helper functions for Notion integration, email sending,
and other utility operations.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class NotionClient:
    """Notion API client for posting AI news summaries."""
    
    def __init__(self):
        """Initialize Notion client."""
        self.token = os.getenv('NOTION_TOKEN')
        self.database_id = os.getenv('NOTION_DATABASE_ID')
        
        if not self.token or not self.database_id:
            logger.warning("Notion credentials not configured")
            return
        
        try:
            from notion_client import Client
            self.client = Client(auth=self.token)
        except ImportError:
            logger.error("notion-client not installed. Install with: pip install notion-client")
            self.client = None
    
    def create_page(self, title: str, content: str, date: str) -> bool:
        """
        Create a new page in Notion with AI news summary.
        
        Args:
            title: Page title
            content: Page content (markdown)
            date: Date string
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            # Convert markdown to Notion blocks
            blocks = self._markdown_to_notion_blocks(content)
            
            # Get day of week
            from datetime import datetime
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            day_name = date_obj.strftime('%A')  # Monday, Tuesday, etc.
            
            # Get current time for posting
            current_time = datetime.now().strftime('%I:%M %p').lower()  # 9:00 am
            
            # Get top story headline (first article title)
            top_story = "No articles found"
            if blocks and len(blocks) > 0:
                # Look for the first heading that contains article title
                for block in blocks:
                    if block.get('type') == 'heading_3':
                        top_story = block.get('heading_3', {}).get('rich_text', [{}])[0].get('text', {}).get('content', 'No title')
                        break
            
            # Create page with new format
            try:
                # Try with Time Posted property
                response = self.client.pages.create(
                    parent={"database_id": self.database_id},
                    properties={
                        "Title": {"title": [{"text": {"content": f"Top AI News: {day_name}"}}]},
                        "Date": {"date": {"start": date}},
                        "Summary": {"rich_text": [{"text": {"content": top_story}}]},
                        "Time Posted": {"rich_text": [{"text": {"content": current_time}}]}
                    },
                    children=blocks
                )
            except Exception as e:
                if "Time Posted is not a property" in str(e):
                    # Fallback without Time Posted property
                    logger.info("Time Posted property not found, creating page without it")
                    response = self.client.pages.create(
                        parent={"database_id": self.database_id},
                        properties={
                            "Title": {"title": [{"text": {"content": f"Top AI News: {day_name}"}}]},
                            "Date": {"date": {"start": date}},
                            "Summary": {"rich_text": [{"text": {"content": top_story}}]}
                        },
                        children=blocks
                    )
                else:
                    raise e
            
            logger.info(f"Created Notion page: {response['url']}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating Notion page: {e}")
            return False
    
    def _markdown_to_notion_blocks(self, markdown_content: str) -> List[dict]:
        """
        Convert markdown content to Notion blocks.
        
        Args:
            markdown_content: Markdown content
            
        Returns:
            List of Notion block objects
        """
        blocks = []
        lines = markdown_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('# '):
                # Heading 1
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    }
                })
            elif line.startswith('## '):
                # Heading 2
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                    }
                })
            elif line.startswith('### '):
                # Heading 3
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
                    }
                })
            elif line.startswith('**') and line.endswith('**'):
                # Bold text
                content = line[2:-2]
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": content},
                            "annotations": {"bold": True}
                        }]
                    }
                })
            elif line.startswith('**Link:**'):
                # Handle links - convert to clickable URL blocks
                link_text = line.replace('**Link:**', '').strip()
                if link_text.startswith('http'):
                    # Create a clickable URL block
                    blocks.append({
                        "object": "block",
                        "type": "bookmark",
                        "bookmark": {
                            "url": link_text
                        }
                    })
                else:
                    # Fallback to regular paragraph if not a valid URL
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": line}}]
                        }
                    })
            else:
                # Regular paragraph
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": line}}]
                    }
                })
        
        return blocks


class EmailClient:
    """Email client for sending AI news summaries."""
    
    def __init__(self):
        """Initialize email client."""
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.recipient_email = os.getenv('RECIPIENT_EMAIL')
        
        if not all([self.smtp_server, self.email_user, self.email_password, self.recipient_email]):
            logger.warning("Email credentials not fully configured")
    
    def send_email(self, subject: str, content: str, date: str) -> bool:
        """
        Send email with AI news summary.
        
        Args:
            subject: Email subject
            content: Email content (HTML)
            date: Date string
            
        Returns:
            True if successful, False otherwise
        """
        if not all([self.smtp_server, self.email_user, self.email_password, self.recipient_email]):
            logger.error("Email credentials not configured")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_user
            msg['To'] = self.recipient_email
            
            # Convert markdown to HTML
            html_content = self._markdown_to_html(content)
            
            # Attach HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {self.recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def _markdown_to_html(self, markdown_content: str) -> str:
        """
        Convert markdown content to HTML.
        
        Args:
            markdown_content: Markdown content
            
        Returns:
            HTML content
        """
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; }}
                h2 {{ color: #34495e; }}
                h3 {{ color: #7f8c8d; }}
                a {{ color: #3498db; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                .article {{ margin-bottom: 30px; padding: 15px; border-left: 4px solid #3498db; background: #f8f9fa; }}
                .source {{ color: #7f8c8d; font-size: 0.9em; }}
                .summary {{ margin: 10px 0; }}
            </style>
        </head>
        <body>
        """
        
        lines = markdown_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('# '):
                html += f"<h1>{line[2:]}</h1>"
            elif line.startswith('## '):
                html += f"<h2>{line[3:]}</h2>"
            elif line.startswith('### '):
                html += f"<h3>{line[4:]}</h3>"
            elif line.startswith('**Source:**'):
                source = line.replace('**Source:**', '').strip()
                html += f'<div class="source"><strong>Source:</strong> {source}</div>'
            elif line.startswith('**Summary:**'):
                summary = line.replace('**Summary:**', '').strip()
                html += f'<div class="summary"><strong>Summary:</strong> {summary}</div>'
            elif line.startswith('**Link:**'):
                link = line.replace('**Link:**', '').strip()
                html += f'<div><strong>Link:</strong> <a href="{link}" target="_blank">{link}</a></div>'
            elif line == '---':
                html += '<hr>'
            else:
                html += f"<p>{line}</p>"
        
        html += "</body></html>"
        return html


def setup_logging(log_level: str = 'INFO') -> None:
    """
    Setup logging configuration.
    
    Args:
        log_level: Logging level
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('ai_news_agent.log'),
            logging.StreamHandler()
        ]
    )


def validate_environment() -> bool:
    """
    Validate that all required environment variables are set.
    
    Returns:
        True if all required variables are set, False otherwise
    """
    required_vars = ['OPENAI_API_KEY']
    optional_vars = ['NOTION_TOKEN', 'NOTION_DATABASE_ID', 'SMTP_SERVER', 'EMAIL_USER', 'EMAIL_PASSWORD', 'RECIPIENT_EMAIL']
    
    missing_required = []
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    if missing_required:
        logger.error(f"Missing required environment variables: {missing_required}")
        return False
    
    logger.info("Environment validation passed")
    return True 