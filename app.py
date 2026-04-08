"""
Main Streamlit application for the AI News Email App (cat_fetches).
Implements Apple-inspired UI design with topic selection, tone options, and length preferences.
"""

# Load environment variables first before any other imports
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not available, skip .env loading
    pass

import streamlit as st
from enum import Enum
from typing import Optional
import os

from services.news_service import NewsService, validate_topic
from services.logging_service import logger, log_info, log_error, ErrorIds
from services.ai_service import AIService, SummaryRequest, ToneStyle, LengthMode
from services.email_service import EmailService, EmailRequest


class ToneOption(Enum):
    """Available tone options for news summaries."""
    CONCISE = "Concise"
    PROFESSIONAL = "Professional"
    ANALYTICAL = "Analytical"
    CASUAL = "Casual"


class LengthMode(Enum):
    """Available length modes for news summaries."""
    TLDR = "TLDR"
    DEEP_DIVE = "Deep Dive"


def init_page_config():
    """Initialize Streamlit page configuration."""
    st.set_page_config(
        page_title="cat_fetches - news summaries",
        page_icon="📰",
        layout="centered",
        initial_sidebar_state="collapsed",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': "get news summaries sent to your email"
        }
    )


def load_apple_design_css():
    """Load Apple design system CSS."""
    css_path = os.path.join(os.path.dirname(__file__), "static", "apple_design.css")

    try:
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()

        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

        log_info(logger, "Apple design CSS loaded successfully")

    except FileNotFoundError:
        log_error(logger, "Apple design CSS file not found", ErrorIds.CONFIG_LOAD_FAILED,
                 css_path=css_path)
        st.error("couldn't load the design. using default look.")
    except Exception as e:
        log_error(logger, "Error loading Apple design CSS", ErrorIds.CONFIG_LOAD_FAILED,
                 css_path=css_path, error_details=str(e))


def validate_form_inputs(topic: str, tone: str, length: str, email: str) -> Optional[str]:
    """
    Validate form inputs and return error message if invalid.

    Args:
        topic: User-provided news topic
        tone: Selected tone option
        length: Selected length mode
        email: Recipient email address

    Returns:
        Error message if validation fails, None if valid
    """
    try:
        # Validate topic using the existing validation function
        validate_topic(topic)

        # Validate tone is in allowed options
        tone_values = [option.value for option in ToneOption]
        if tone not in tone_values:
            return f"pick one of these tones: {', '.join(tone_values)}"

        # Validate length is in allowed options
        length_values = [option.value for option in LengthMode]
        if length not in length_values:
            return f"pick one of these lengths: {', '.join(length_values)}"

        # Validate email address
        if not email or not email.strip():
            return "need an email address"

        email = email.strip()
        if '@' not in email or '.' not in email.split('@')[1]:
            return "that doesn't look like an email address"

        if len(email) > 254:  # RFC 5321 limit
            return "email address is too long"

        return None

    except ValueError as e:
        return str(e)


def render_header():
    """Render the application header section."""
    st.markdown("""
        <div class="header-section">
            <h1 class="app-title">cat_fetches</h1>
            <p class="app-subtitle">get news summaries sent to your email</p>
        </div>
    """, unsafe_allow_html=True)


def render_topic_input() -> str:
    """Render topic input field with validation."""
    st.markdown('<div class="input-section">', unsafe_allow_html=True)

    topic = st.text_input(
        "what topic do you want news about?",
        placeholder="e.g., artificial intelligence, climate change, technology trends",
        max_chars=100,
        key="topic_input",
        help="any topic you want to read about"
    )

    st.markdown('</div>', unsafe_allow_html=True)
    return topic


def render_email_input() -> str:
    """Render email input field for delivery."""
    st.markdown('<div class="input-section">', unsafe_allow_html=True)

    email = st.text_input(
        "your email address",
        placeholder="your.email@example.com",
        key="email_input",
        help="where to send your news summary"
    )

    st.markdown('</div>', unsafe_allow_html=True)
    return email


def render_preferences() -> tuple[str, str]:
    """Render tone and length preference controls."""
    st.markdown('<div class="preferences-section">', unsafe_allow_html=True)

    # Create two columns for preferences
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**tone**")
        tone = st.selectbox(
            "pick a tone",
            options=[option.value for option in ToneOption],
            index=0,  # Default to Concise
            key="tone_select",
            label_visibility="collapsed"
        )

    with col2:
        st.markdown("**length**")
        length = st.selectbox(
            "pick a length",
            options=[option.value for option in LengthMode],
            index=0,  # Default to TLDR
            key="length_select",
            label_visibility="collapsed"
        )

    # Add helpful descriptions
    if length == LengthMode.TLDR.value:
        st.markdown('<p class="length-description">tldr: 5-8 bullet points, under 200 words</p>',
                   unsafe_allow_html=True)
    else:
        st.markdown('<p class="length-description">deep dive: 400-800 words with more details</p>',
                   unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    return tone, length


def render_generate_button() -> bool:
    """Render the generate & send button."""
    st.markdown('<div class="button-section">', unsafe_allow_html=True)

    button_clicked = st.button(
        "get my news summary",
        key="generate_button",
        type="primary",
        use_container_width=True
    )

    st.markdown('</div>', unsafe_allow_html=True)
    return button_clicked


def process_news_request(topic: str, tone: str, length: str, email: str) -> bool:
    """
    Process the news request with AI summary generation and email delivery.

    Args:
        topic: News topic to search for
        tone: Tone preference for summary
        length: Length preference for summary
        email: Recipient email address

    Returns:
        True if successful, False if error occurred
    """
    try:
        # Log the user request for monitoring
        log_info(logger, "Processing news request",
                topic=topic, tone=tone, length=length, recipient_email=email)

        # Step 1: Fetch news articles
        st.info("🔍 looking for articles...")
        news_service = NewsService()
        articles = news_service.fetch_articles(topic, max_articles=10)

        if not articles:
            st.error("couldn't find any articles for this topic. try something else?")
            return False

        st.success(f"found {len(articles)} articles about '{topic}'")

        # Step 2: Generate AI summary
        try:
            st.info("🤖 writing your summary...")

            # Convert string values to enums
            tone_enum = ToneStyle(tone.lower())
            length_enum = LengthMode.TLDR if length == "TLDR" else LengthMode.DEEP_DIVE

            # Initialize AI service
            ai_service = AIService()

            # Create summary request
            summary_request = SummaryRequest(
                articles=articles,
                topic=topic,
                tone=tone_enum,
                length_mode=length_enum
            )

            # Generate summary
            summary_response = ai_service.generate_summary(summary_request)

            # Display the generated summary
            st.success("✨ summary ready!")

            # Show summary metadata
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("articles used", summary_response.articles_processed)
            with col2:
                st.metric("words", summary_response.word_count)
            with col3:
                st.metric("tone", summary_response.tone_used.title())

            # Display the summary content
            st.markdown("### 📰 your news summary")

            # Style the summary content based on length mode
            if summary_response.length_mode_used == "tldr":
                st.markdown("**tldr format:**")
            else:
                st.markdown("**deep dive:**")

            st.markdown("---")
            st.markdown(summary_response.content)
            st.markdown("---")

            # Step 3: Email delivery
            st.info("📧 sending to your email...")

            try:
                # Initialize email service
                email_service = EmailService()

                # Create email request
                subject = f"news summary: {topic.title()} ({length} • {tone})"
                email_request = EmailRequest(
                    recipient_email=email,
                    subject=subject,
                    summary=summary_response,
                    articles=articles
                )

                # Send email
                email_response = email_service.send_summary_email(email_request)

                if email_response.success:
                    st.success(f"✅ sent to {email}!")

                    # Show delivery details
                    with st.expander("📬 email details", expanded=False):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**sent to:** {email_response.recipient}")
                            st.write(f"**subject:** {email_response.subject}")
                        with col2:
                            st.write(f"**when:** {email_response.delivery_time}")
                            st.write(f"**format:** {email_response.format_used}")

                else:
                    st.error("❌ couldn't send the email. try again?")
                    return False

            except Exception as email_error:
                log_error(logger, "Email delivery failed", ErrorIds.NEWS_API_HTTP_ERROR,
                         topic=topic, tone=tone, length=length, email=email,
                         error_details=str(email_error))
                st.error("⚠️ couldn't send email, but your summary is ready above")
                # The summary is already displayed above, so user still gets value

            # Show article sources for reference
            with st.expander("📚 sources used", expanded=False):
                for i, article in enumerate(articles[:summary_response.articles_processed], 1):
                    st.markdown(f"**{i}. {article.title}**")
                    st.markdown(f"*from: {article.source_name}*")
                    st.markdown(f"🔗 [read full article]({article.url})")
                    st.markdown("---")

            return True

        except Exception as ai_error:
            log_error(logger, "AI summary generation failed", ErrorIds.NEWS_API_HTTP_ERROR,
                     topic=topic, tone=tone, length=length, email=email, error_details=str(ai_error))

            # Show articles even if AI fails
            st.error("⚠️ couldn't make a summary, but here are the articles i found:")

            with st.expander("📚 articles about your topic", expanded=True):
                for i, article in enumerate(articles[:5], 1):
                    st.markdown(f"**{i}. {article.title}**")
                    st.markdown(f"*from: {article.source_name}*")
                    if article.description:
                        st.markdown(f"{article.description}")
                    st.markdown(f"🔗 [read more]({article.url})")
                    st.markdown("---")

            return True  # Still successful since we got articles

    except Exception as e:
        log_error(logger, "News request processing failed", ErrorIds.NEWS_API_HTTP_ERROR,
                 topic=topic, tone=tone, length=length, email=email, error_details=str(e))
        st.error("something went wrong. want to try again?")
        return False


def main():
    """Main application entry point."""
    # Initialize page configuration
    init_page_config()

    # Apply Apple design system CSS
    load_apple_design_css()

    # Render header
    render_header()

    # Create main form
    with st.form("news_request_form", clear_on_submit=False):
        # Topic input
        topic = render_topic_input()

        # Add spacing
        st.markdown('<div class="form-spacer"></div>', unsafe_allow_html=True)

        # Email input
        email = render_email_input()

        # Add spacing
        st.markdown('<div class="form-spacer"></div>', unsafe_allow_html=True)

        # Preferences
        tone, length = render_preferences()

        # Add spacing
        st.markdown('<div class="form-spacer"></div>', unsafe_allow_html=True)

        # Generate button
        submitted = st.form_submit_button(
            "get my news summary",
            type="primary",
            use_container_width=True
        )

    # Process form submission
    if submitted:
        # Validate inputs
        validation_error = validate_form_inputs(topic, tone, length, email)

        if validation_error:
            st.error(f"⚠️ {validation_error}")
            log_error(logger, "Form validation failed", ErrorIds.INPUT_INVALID_TOPIC,
                     topic=topic, tone=tone, length=length, email=email, validation_error=validation_error)
        else:
            # Process the request
            with st.spinner("working on it..."):
                success = process_news_request(topic, tone, length, email)

            if success:
                log_info(logger, "News request completed successfully",
                        topic=topic, tone=tone, length=length, email=email)


if __name__ == "__main__":
    main()
