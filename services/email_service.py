"""
Email service for sending AI-generated news summaries via SMTP.
Implements secure email delivery with Apple-inspired templates.
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.utils import formataddr, formatdate
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
import html

from config import settings
from services.news_service import NewsArticle
from services.ai_service import SummaryResponse
from services.logging_service import logger, log_error, log_warning, log_info, ErrorIds


# Constants
SMTP_TIMEOUT = 30  # seconds
MAX_RETRY_ATTEMPTS = 3
EMAIL_SUBJECT_MAX_LENGTH = 78  # RFC 2822 recommendation


@dataclass
class EmailRequest:
    """Request structure for email delivery."""
    recipient_email: str
    subject: str
    summary: SummaryResponse
    articles: List[NewsArticle]
    sender_name: Optional[str] = "cat_fetches News"


@dataclass
class EmailResponse:
    """Response structure for email delivery."""
    success: bool
    message_id: Optional[str]
    recipient: str
    subject: str
    delivery_time: str
    format_used: str  # 'html', 'text', or 'both'


class EmailTemplates:
    """Apple-inspired email templates for news summaries."""

    @staticmethod
    def generate_html_template(summary: SummaryResponse, articles: List[NewsArticle]) -> str:
        """
        Generate Apple-inspired HTML email template.

        Args:
            summary: AI-generated summary
            articles: Source articles

        Returns:
            Complete HTML email content
        """
        # Apple-inspired color scheme
        colors = {
            'apple_blue': '#0071e3',
            'near_black': '#1d1d1f',
            'light_gray': '#f5f5f7',
            'text_secondary': 'rgba(0, 0, 0, 0.8)',
            'text_tertiary': 'rgba(0, 0, 0, 0.48)',
            'white': '#ffffff'
        }

        # Generate article sources section
        sources_html = ""
        for i, article in enumerate(articles, 1):
            sources_html += f"""
            <tr>
                <td style="padding: 12px 0; border-bottom: 1px solid #f0f0f0;">
                    <h4 style="margin: 0 0 4px 0; color: {colors['near_black']}; font-size: 16px; font-weight: 600;">
                        {i}. {html.escape(article.title)}
                    </h4>
                    <p style="margin: 0 0 4px 0; color: {colors['text_secondary']}; font-size: 14px; font-style: italic;">
                        Source: {html.escape(article.source_name)}
                    </p>
                    <a href="{html.escape(article.url)}"
                       style="color: {colors['apple_blue']}; text-decoration: none; font-size: 14px; font-weight: 500;">
                        Read full article →
                    </a>
                </td>
            </tr>"""

        # Format summary content with proper HTML
        summary_html = html.escape(summary.content).replace('\n', '<br>')

        # Handle different summary formats
        if summary.length_mode_used == 'tldr':
            # Convert bullet points to proper HTML list if present
            if '•' in summary_html or '-' in summary_html:
                lines = summary_html.split('<br>')
                list_items = []
                for line in lines:
                    line = line.strip()
                    if line.startswith('•') or line.startswith('-'):
                        list_items.append(f"<li>{line[1:].strip()}</li>")
                    elif line:
                        list_items.append(f"<li>{line}</li>")
                if list_items:
                    summary_html = f"<ul style='margin: 0; padding-left: 20px;'>{''.join(list_items)}</ul>"

        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your News Summary - cat_fetches</title>
    <style>
        /* Import system fonts similar to Apple's SF Pro */
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: {colors['light_gray']};
            line-height: 1.6;
        }}
    </style>
</head>
<body>
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: {colors['light_gray']};">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <!-- Main container -->
                <table width="600" cellpadding="0" cellspacing="0" style="max-width: 600px; background-color: {colors['white']}; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">

                    <!-- Header -->
                    <tr>
                        <td style="padding: 40px 40px 30px 40px; text-align: center; background-color: {colors['near_black']}; border-radius: 12px 12px 0 0;">
                            <h1 style="margin: 0; color: {colors['white']}; font-size: 32px; font-weight: 600; letter-spacing: -0.5px;">
                                cat_fetches
                            </h1>
                            <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.8); font-size: 16px; font-weight: 400;">
                                Your personalized news summary
                            </p>
                        </td>
                    </tr>

                    <!-- Summary metadata -->
                    <tr>
                        <td style="padding: 30px 40px 20px 40px;">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="padding: 15px; background-color: {colors['light_gray']}; border-radius: 8px; text-align: center; width: 33.33%;">
                                        <div style="color: {colors['apple_blue']}; font-size: 24px; font-weight: 700; margin-bottom: 4px;">
                                            {summary.articles_processed}
                                        </div>
                                        <div style="color: {colors['text_secondary']}; font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">
                                            Articles
                                        </div>
                                    </td>
                                    <td style="width: 2%;"></td>
                                    <td style="padding: 15px; background-color: {colors['light_gray']}; border-radius: 8px; text-align: center; width: 33.33%;">
                                        <div style="color: {colors['apple_blue']}; font-size: 24px; font-weight: 700; margin-bottom: 4px;">
                                            {summary.word_count}
                                        </div>
                                        <div style="color: {colors['text_secondary']}; font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">
                                            Words
                                        </div>
                                    </td>
                                    <td style="width: 2%;"></td>
                                    <td style="padding: 15px; background-color: {colors['light_gray']}; border-radius: 8px; text-align: center; width: 33.33%;">
                                        <div style="color: {colors['apple_blue']}; font-size: 24px; font-weight: 700; margin-bottom: 4px;">
                                            {summary.tone_used.title()}
                                        </div>
                                        <div style="color: {colors['text_secondary']}; font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">
                                            Tone
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Summary content -->
                    <tr>
                        <td style="padding: 0 40px 30px 40px;">
                            <h2 style="margin: 0 0 20px 0; color: {colors['near_black']}; font-size: 24px; font-weight: 600; letter-spacing: -0.3px;">
                                📰 {html.escape(summary.topic.title())} News Summary
                            </h2>
                            <div style="color: {colors['text_secondary']}; font-size: 17px; line-height: 1.6; margin-bottom: 25px;">
                                {summary_html}
                            </div>

                            <div style="padding: 20px; background-color: {colors['light_gray']}; border-radius: 8px; border-left: 4px solid {colors['apple_blue']};">
                                <p style="margin: 0; color: {colors['text_secondary']}; font-size: 14px; font-style: italic;">
                                    <strong>Format:</strong> {summary.length_mode_used.replace('_', ' ').title()} •
                                    <strong>Generated:</strong> {datetime.now().strftime("%B %d, %Y at %I:%M %p")}
                                </p>
                            </div>
                        </td>
                    </tr>

                    <!-- Article sources -->
                    <tr>
                        <td style="padding: 0 40px 40px 40px;">
                            <h3 style="margin: 0 0 20px 0; color: {colors['near_black']}; font-size: 20px; font-weight: 600;">
                                📚 Sources
                            </h3>
                            <table width="100%" cellpadding="0" cellspacing="0" style="border-top: 2px solid {colors['apple_blue']};">
                                {sources_html}
                            </table>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 30px 40px; background-color: {colors['light_gray']}; border-radius: 0 0 12px 12px; text-align: center;">
                            <p style="margin: 0; color: {colors['text_tertiary']}; font-size: 12px;">
                                Powered by <strong>cat_fetches</strong> • AI-driven news summaries<br>
                                Generated on {datetime.now().strftime("%A, %B %d, %Y")}
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
        return html_template

    @staticmethod
    def generate_text_template(summary: SummaryResponse, articles: List[NewsArticle]) -> str:
        """
        Generate plain text email template.

        Args:
            summary: AI-generated summary
            articles: Source articles

        Returns:
            Complete plain text email content
        """
        # Header
        text_content = f"""
cat_fetches - Your Personalized News Summary
=========================================

Topic: {summary.topic.title()}
Tone: {summary.tone_used.title()}
Format: {summary.length_mode_used.replace('_', ' ').title()}
Articles Processed: {summary.articles_processed}
Word Count: {summary.word_count}
Generated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}

=========================================

{summary.content}

=========================================
SOURCES
=========================================
"""

        # Add article sources
        for i, article in enumerate(articles, 1):
            text_content += f"""
{i}. {article.title}
   Source: {article.source_name}
   URL: {article.url}
"""

        # Footer
        text_content += f"""
=========================================

Powered by cat_fetches - AI-driven news summaries
Generated on {datetime.now().strftime("%A, %B %d, %Y")}
"""

        return text_content.strip()


class EmailService:
    """
    Service for sending news summary emails via secure SMTP.
    Supports both HTML and plain text formats with Apple-inspired design.
    """

    def __init__(self):
        """Initialize the email service with SMTP configuration."""
        try:
            self.smtp_server = settings.smtp_server
            self.smtp_port = settings.smtp_port
            self.smtp_email = settings.smtp_email
            self.smtp_password = settings.smtp_password

            # Validate configuration
            if not all([self.smtp_server, self.smtp_port, self.smtp_email, self.smtp_password]):
                raise ValueError("Incomplete SMTP configuration")

            log_info(logger, "Email service initialized successfully",
                    smtp_server=self.smtp_server, smtp_port=self.smtp_port)

        except Exception as e:
            log_error(logger, "Failed to initialize email service", ErrorIds.CONFIG_LOAD_FAILED,
                     error_details=str(e))
            raise RuntimeError("Email service initialization failed") from e

    def send_summary_email(self, request: EmailRequest) -> EmailResponse:
        """
        Send a news summary email to the specified recipient.

        Args:
            request: EmailRequest with recipient, subject, summary, and articles

        Returns:
            EmailResponse with delivery status and metadata

        Raises:
            RuntimeError: If email delivery fails
        """
        try:
            # Validate request
            self._validate_email_request(request)

            # Generate email content
            html_content = EmailTemplates.generate_html_template(request.summary, request.articles)
            text_content = EmailTemplates.generate_text_template(request.summary, request.articles)

            # Create email message
            message = self._create_email_message(
                recipient_email=request.recipient_email,
                subject=request.subject,
                html_content=html_content,
                text_content=text_content,
                sender_name=request.sender_name or "cat_fetches News"
            )

            # Send email with retry logic
            message_id = self._send_with_retry(message, request.recipient_email)

            # Create response
            response = EmailResponse(
                success=True,
                message_id=message_id,
                recipient=request.recipient_email,
                subject=request.subject,
                delivery_time=datetime.now().isoformat(),
                format_used="both"  # HTML and text
            )

            log_info(logger, "Email sent successfully",
                    recipient=request.recipient_email,
                    subject=request.subject,
                    message_id=message_id,
                    articles_count=len(request.articles))

            return response

        except Exception as e:
            log_error(logger, "Email delivery failed", ErrorIds.NEWS_API_HTTP_ERROR,
                     recipient=request.recipient_email,
                     subject=request.subject,
                     error_details=str(e))
            raise RuntimeError("Failed to send email") from e

    def _validate_email_request(self, request: EmailRequest) -> None:
        """Validate the email request parameters."""
        if not request.recipient_email or '@' not in request.recipient_email:
            raise ValueError("Invalid recipient email address")

        if not request.subject or len(request.subject.strip()) == 0:
            raise ValueError("Email subject cannot be empty")

        if len(request.subject) > EMAIL_SUBJECT_MAX_LENGTH:
            raise ValueError(f"Email subject too long (max {EMAIL_SUBJECT_MAX_LENGTH} characters)")

        if not request.summary or not request.summary.content:
            raise ValueError("Summary content cannot be empty")

        if not request.articles:
            raise ValueError("At least one source article required")

    def _create_email_message(self, recipient_email: str, subject: str,
                            html_content: str, text_content: str,
                            sender_name: str) -> MIMEMultipart:
        """
        Create a properly formatted MIME email message.

        Args:
            recipient_email: Recipient email address
            subject: Email subject line
            html_content: HTML email content
            text_content: Plain text email content
            sender_name: Display name for sender

        Returns:
            Complete MIME message ready for sending
        """
        # Create multipart message
        message = MIMEMultipart('alternative')

        # Set headers
        message['From'] = formataddr((sender_name, self.smtp_email))
        message['To'] = recipient_email
        message['Subject'] = subject
        message['Date'] = formatdate(localtime=True)

        # Add custom headers for better deliverability
        message['Message-ID'] = f"<{datetime.now().strftime('%Y%m%d%H%M%S')}.cat_fetches@{self.smtp_server}>"
        message['X-Mailer'] = "cat_fetches News Summarizer v1.0"

        # Attach text and HTML parts
        text_part = MIMEText(text_content, 'plain', 'utf-8')
        html_part = MIMEText(html_content, 'html', 'utf-8')

        message.attach(text_part)
        message.attach(html_part)

        return message

    def _send_with_retry(self, message: MIMEMultipart, recipient_email: str) -> Optional[str]:
        """
        Send email with retry logic and proper error handling.

        Args:
            message: Complete MIME message
            recipient_email: Recipient email address

        Returns:
            Message ID if successful, None if failed
        """
        last_error = None

        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            try:
                log_info(logger, f"Email delivery attempt {attempt}",
                        recipient=recipient_email, attempt=attempt)

                # Create SSL context
                context = ssl.create_default_context()

                # Connect to SMTP server
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=SMTP_TIMEOUT) as server:
                    # Start TLS for security
                    server.starttls(context=context)

                    # Authenticate
                    server.login(self.smtp_email, self.smtp_password)

                    # Send message
                    server.send_message(message, to_addrs=[recipient_email])

                    # Extract message ID
                    message_id = message.get('Message-ID', f"attempt_{attempt}")

                    log_info(logger, "Email sent successfully via SMTP",
                            recipient=recipient_email,
                            attempt=attempt,
                            message_id=message_id)

                    return message_id

            except smtplib.SMTPAuthenticationError as e:
                log_error(logger, "SMTP authentication failed", ErrorIds.CONFIG_INVALID_PORT,
                         attempt=attempt, error_details=str(e))
                raise RuntimeError("Email authentication failed - check credentials") from e

            except smtplib.SMTPRecipientsRefused as e:
                log_error(logger, "SMTP recipient refused", ErrorIds.CONFIG_INVALID_PORT,
                         attempt=attempt, recipient=recipient_email, error_details=str(e))
                raise RuntimeError(f"Recipient email address rejected: {recipient_email}") from e

            except (smtplib.SMTPException, ssl.SSLError, OSError) as e:
                last_error = e
                log_warning(logger, f"Email delivery attempt {attempt} failed, retrying",
                           ErrorIds.NEWS_API_HTTP_ERROR,
                           attempt=attempt, max_attempts=MAX_RETRY_ATTEMPTS,
                           error_details=str(e))

                if attempt == MAX_RETRY_ATTEMPTS:
                    break

        # All attempts failed
        log_error(logger, "All email delivery attempts failed", ErrorIds.NEWS_API_HTTP_ERROR,
                 max_attempts=MAX_RETRY_ATTEMPTS, final_error=str(last_error))
        raise RuntimeError(f"Email delivery failed after {MAX_RETRY_ATTEMPTS} attempts") from last_error