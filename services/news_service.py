"""
News service for fetching articles from NewsAPI.org.
Production-ready with input validation, timeout handling, and security controls.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests

from config import settings
from services.logging_service import logger, log_error, log_warning, log_info, ErrorIds


# Constants
MAX_TOPIC_LENGTH = 100
MAX_TEXT_LENGTH = 5000
MAX_ARTICLES_LIMIT = 20
REQUEST_TIMEOUT = 10
PROCESSING_BUFFER_MULTIPLIER = 2

# Pre-compiled regex patterns for efficiency
TOPIC_VALIDATION_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-.,!?&]+$')
HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
WHITESPACE_PATTERN = re.compile(r'\s+')


@dataclass(frozen=True)
class NewsArticle:
    """Structured representation of a news article with validation."""
    title: str
    description: str
    content: str
    url: str
    image_url: Optional[str]
    published_at: str
    source_name: str

    def __post_init__(self) -> None:
        """Validate article data after initialization."""
        if not self.title or not self.title.strip():
            raise ValueError("Article title cannot be empty")

        if not self.url or not self.url.strip():
            raise ValueError("Article URL cannot be empty")

        if not self.url.startswith("https://"):
            raise ValueError("Article URL must use HTTPS")

        if not self.source_name or not self.source_name.strip():
            raise ValueError("Article source name cannot be empty")

        if self.image_url and not self.image_url.startswith("https://"):
            raise ValueError("Article image URL must use HTTPS")

        if len(self.title) > MAX_TEXT_LENGTH:
            raise ValueError(f"Article title too long (max {MAX_TEXT_LENGTH} characters)")

        if len(self.content) > MAX_TEXT_LENGTH:
            raise ValueError(f"Article content too long (max {MAX_TEXT_LENGTH} characters)")


def validate_topic(topic: str) -> str:
    """
    Validate and sanitize news topic input.

    Args:
        topic: User-provided search topic

    Returns:
        Cleaned topic string

    Raises:
        ValueError: If topic is invalid or unsafe
    """
    if not topic or not topic.strip():
        raise ValueError("Topic cannot be empty")

    topic = topic.strip()
    if len(topic) > MAX_TOPIC_LENGTH:
        raise ValueError(f"Topic must be {MAX_TOPIC_LENGTH} characters or less")

    # Allow only safe characters: alphanumeric, spaces, basic punctuation (no quotes)
    if not TOPIC_VALIDATION_PATTERN.match(topic):
        raise ValueError("Topic contains invalid characters")

    return topic


class NewsService:
    """
    Service for fetching news articles from NewsAPI.org.
    Implements secure request handling with proper error management.
    """

    def __init__(self):
        self.base_url = "https://newsapi.org/v2/everything"
        self.api_key = settings.news_api_key
        self.timeout = REQUEST_TIMEOUT
        self.max_articles = 10

    def fetch_articles(self, topic: str, max_articles: int = 10) -> List[NewsArticle]:
        """
        Fetch news articles for the given topic.

        Args:
            topic: Search topic/query string
            max_articles: Maximum number of articles to return (default: 10)

        Returns:
            List of NewsArticle objects

        Raises:
            ValueError: If topic validation fails
            RuntimeError: If API request fails or returns no results
        """
        try:
            # Validate and sanitize input
            topic = validate_topic(topic)

            # Validate max_articles parameter
            if max_articles < 1:
                raise ValueError("max_articles must be at least 1")
            max_articles = min(max_articles, MAX_ARTICLES_LIMIT)

            # Prepare secure HTTPS request
            headers = {
                "X-API-Key": self.api_key,
                "User-Agent": "cat_fetches-news-app/1.0 (AI News Email Service; https://github.com/yourorg/cat_fetches)",
                "Accept": "application/json"
            }

            params = {
                "q": topic,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": max_articles,
                "excludeDomains": None  # Allow all domains for broader coverage
            }

            # Execute request with timeout protection
            response = requests.get(
                self.base_url,
                headers=headers,
                params=params,
                timeout=self.timeout,
                allow_redirects=False  # Security: prevent redirect attacks
            )

            # Handle HTTP error responses
            self._handle_http_errors(response, topic)

            # Parse and validate JSON response
            data = response.json()
            self._validate_api_response(data)

            # Extract and structure articles
            raw_articles = data.get("articles", [])
            if not raw_articles:
                raise RuntimeError("No articles found for this topic")

            articles = self._parse_articles(raw_articles)

            # Log successful operation for monitoring
            log_info(logger, "Successfully fetched news articles",
                    topic=topic, articles_requested=max_articles,
                    articles_returned=len(articles),
                    articles_available=len(raw_articles))

            return articles

        except requests.exceptions.Timeout as exc:
            log_error(logger, "News API request timeout", ErrorIds.NEWS_API_TIMEOUT,
                     topic=topic, timeout=self.timeout, error_details=str(exc))
            raise RuntimeError("News service timeout - please try again") from exc
        except requests.exceptions.ConnectionError as exc:
            if "SSL" in str(exc).upper():
                log_error(logger, "SSL connection to news API failed", ErrorIds.NEWS_API_SSL_ERROR,
                         topic=topic, error_details=str(exc))
                raise RuntimeError("Secure connection to news service failed") from exc
            else:
                log_error(logger, "Connection to news API failed", ErrorIds.NEWS_API_CONNECTION_ERROR,
                         topic=topic, error_details=str(exc))
                raise RuntimeError("Cannot connect to news service") from exc
        except requests.exceptions.RequestException as exc:
            log_error(logger, "News API request failed", ErrorIds.NEWS_API_HTTP_ERROR,
                     topic=topic, error_details=str(exc))
            raise RuntimeError("News service unavailable") from exc
        except ValueError:
            raise  # Re-raise validation errors as-is
        except KeyError as exc:
            log_error(logger, "API response missing expected field", ErrorIds.NEWS_API_HTTP_ERROR,
                     topic=topic, missing_field=str(exc), error_type="KeyError")
            raise RuntimeError("News service returned incomplete data") from exc
        except TypeError as exc:
            log_error(logger, "API response data type mismatch", ErrorIds.NEWS_API_HTTP_ERROR,
                     topic=topic, error_details=str(exc), error_type="TypeError")
            raise RuntimeError("News service returned invalid data format") from exc
        except AttributeError as exc:
            log_error(logger, "Unexpected API response structure", ErrorIds.NEWS_API_HTTP_ERROR,
                     topic=topic, error_details=str(exc), error_type="AttributeError")
            raise RuntimeError("News service response format has changed") from exc

    def _handle_http_errors(self, response: requests.Response, topic: str = "") -> None:
        """Handle HTTP error status codes with appropriate error messages."""
        if response.status_code == 200:
            return

        # Log HTTP errors with context for debugging
        error_id = ErrorIds.NEWS_API_RATE_LIMIT if response.status_code == 429 else ErrorIds.NEWS_API_HTTP_ERROR
        if response.status_code == 401:
            error_id = ErrorIds.NEWS_API_AUTH_ERROR

        log_error(logger, f"News API HTTP error {response.status_code}", error_id,
                 status_code=response.status_code,
                 topic=topic,
                 response_headers=dict(response.headers),
                 url=response.url)

        error_messages = {
            400: "Invalid news topic or parameters",
            401: "News API authentication failed - check API key",
            403: "News API access forbidden - check account status",
            429: "News API rate limit exceeded - try again later",
            500: "News service temporarily unavailable"
        }

        error_msg = error_messages.get(response.status_code, f"News API error: {response.status_code}")
        raise RuntimeError(error_msg)

    def _validate_api_response(self, data: Dict) -> None:
        """Validate the structure and content of the API response."""
        if not isinstance(data, dict):
            raise RuntimeError("Invalid response format from news service")

        if data.get("status") != "ok":
            error_msg = data.get("message", "Unknown API error")
            # Sanitize error message to prevent information disclosure
            if "API key" in error_msg.lower():
                raise RuntimeError("News API authentication error")
            raise RuntimeError(f"News service error: {error_msg}")

    def _parse_articles(self, raw_articles: List[Dict]) -> List[NewsArticle]:
        """
        Parse raw API articles into structured NewsArticle objects.
        Filters out invalid articles and limits results.
        """
        articles = []

        for article_data in raw_articles[:self.max_articles * PROCESSING_BUFFER_MULTIPLIER]:  # Process extra to account for filtering
            try:
                article = self._create_article(article_data)
                if article:
                    articles.append(article)
                    if len(articles) >= self.max_articles:
                        break
            except KeyError as exc:
                # Missing expected field in article data
                log_warning(logger, "Article missing required field, skipping", ErrorIds.ARTICLE_PARSE_FAILED,
                           article_title=article_data.get("title", "unknown"),
                           article_url=article_data.get("url", "unknown"),
                           missing_field=str(exc), error_type="KeyError")
                continue
            except TypeError as exc:
                # Data type mismatch in article data
                log_warning(logger, "Article data type error, skipping", ErrorIds.ARTICLE_PARSE_FAILED,
                           article_title=article_data.get("title", "unknown"),
                           article_url=article_data.get("url", "unknown"),
                           error_details=str(exc), error_type="TypeError")
                continue
            except AttributeError as exc:
                # Unexpected structure in article data
                log_warning(logger, "Article structure error, skipping", ErrorIds.ARTICLE_PARSE_FAILED,
                           article_title=article_data.get("title", "unknown"),
                           article_url=article_data.get("url", "unknown"),
                           error_details=str(exc), error_type="AttributeError")
                continue

        if not articles:
            log_warning(logger, "No valid articles found after parsing", ErrorIds.NO_VALID_ARTICLES,
                       total_raw_articles=len(raw_articles),
                       parsing_failures=len(raw_articles))
            raise RuntimeError("No valid articles found for this topic")

        return articles

    def _create_article(self, data: Dict) -> Optional[NewsArticle]:
        """Create a NewsArticle from raw API data with validation."""
        title = data.get("title", "")
        url = data.get("url", "")

        # Skip articles missing critical data or removed articles
        if not title or not url or "[Removed]" in title or not url.startswith("https://"):
            return None

        image_url = data.get("urlToImage")
        validated_image_url = image_url if self._is_valid_image_url(image_url) else None

        try:
            return NewsArticle(
                title=self._sanitize_text(title),
                description=self._sanitize_text(data.get("description", "")),
                content=self._sanitize_text(data.get("content", "")),
                url=url,
                image_url=validated_image_url,
                published_at=data.get("publishedAt", ""),
                source_name=self._sanitize_text(data.get("source", {}).get("name", "Unknown"))
            )
        except ValueError as exc:
            # Log validation failures for monitoring
            log_warning(logger, "Article validation failed during creation", ErrorIds.ARTICLE_VALIDATION_FAILED,
                       article_title=title, article_url=url, validation_error=str(exc))
            return None

    def _sanitize_text(self, text: str) -> str:
        """Sanitize and clean text content for security and readability."""
        if not text:
            return ""

        # Remove HTML tags and normalize whitespace using pre-compiled patterns
        text = HTML_TAG_PATTERN.sub('', text)
        text = WHITESPACE_PATTERN.sub(' ', text).strip()

        # Limit text length to prevent memory issues
        if len(text) > MAX_TEXT_LENGTH:
            text = text[:MAX_TEXT_LENGTH] + "..."

        return text

    def _is_valid_image_url(self, url: Optional[str]) -> bool:
        """Check if image URL is valid and secure."""
        if not url:
            return False

        # Only allow HTTPS image URLs
        if not url.startswith("https://"):
            return False

        # Check for common image file extensions
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
        return any(ext in url.lower() for ext in image_extensions)
