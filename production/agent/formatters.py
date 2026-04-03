"""Response formatters for different channels.

This module provides channel-specific formatting for agent responses,
ensuring messages are optimized for each communication channel.
"""

import re
from typing import Optional


# ============================================================================
# Main Formatting Function
# ============================================================================

def format_response_for_channel(response: str, channel: str) -> str:
    """Format agent response for specific channel.

    Args:
        response: Raw agent response
        channel: Communication channel (email, whatsapp, web_form)

    Returns:
        Formatted response optimized for the channel
    """
    formatters = {
        'email': format_for_email,
        'whatsapp': format_for_whatsapp,
        'web_form': format_for_web_form
    }

    formatter = formatters.get(channel, format_for_web_form)
    return formatter(response)


# ============================================================================
# Email Formatting
# ============================================================================

def format_for_email(response: str) -> str:
    """Format response for email channel.

    Email characteristics:
    - Formal and professional
    - Can be longer and detailed
    - Proper structure with paragraphs
    - Bullet points and numbered lists preserved
    - No length restrictions

    Args:
        response: Raw response

    Returns:
        Email-formatted response
    """
    # Email can handle the full response as-is
    # Just ensure proper paragraph spacing
    formatted = response.strip()

    # Ensure double line breaks between paragraphs for readability
    formatted = re.sub(r'\n{3,}', '\n\n', formatted)

    return formatted


# ============================================================================
# WhatsApp Formatting
# ============================================================================

def format_for_whatsapp(response: str) -> str:
    """Format response for WhatsApp channel.

    WhatsApp characteristics:
    - Conversational and concise
    - Maximum 1600 characters
    - Short paragraphs (2-3 sentences)
    - Emojis acceptable
    - Mobile-optimized (scannable)

    Args:
        response: Raw response

    Returns:
        WhatsApp-formatted response
    """
    # Remove formal greetings if present
    response = _remove_formal_greetings(response)

    # Break long paragraphs into shorter ones
    response = _break_long_paragraphs(response, max_sentences=3)

    # Truncate if too long (WhatsApp limit is 1600 chars)
    if len(response) > 1600:
        response = _truncate_smartly(response, max_length=1597) + "..."

    # Ensure single line breaks between short paragraphs
    response = re.sub(r'\n{2,}', '\n\n', response)

    return response.strip()


def _remove_formal_greetings(text: str) -> str:
    """Remove formal email-style greetings.

    Args:
        text: Input text

    Returns:
        Text without formal greetings
    """
    # Remove common formal greetings
    patterns = [
        r'^Dear [^,]+,\s*',
        r'^Hello [^,]+,\s*',
        r'^Hi [^,]+,\s*',
        r'^Thank you for contacting us\.\s*',
        r'^Thank you for reaching out\.\s*'
    ]

    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)

    # Remove formal closings
    closing_patterns = [
        r'\n\nBest regards,?\s*\n.*$',
        r'\n\nSincerely,?\s*\n.*$',
        r'\n\nKind regards,?\s*\n.*$',
        r'\n\nThank you,?\s*\n.*$'
    ]

    for pattern in closing_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    return text


def _break_long_paragraphs(text: str, max_sentences: int = 3) -> str:
    """Break long paragraphs into shorter ones.

    Args:
        text: Input text
        max_sentences: Maximum sentences per paragraph

    Returns:
        Text with shorter paragraphs
    """
    paragraphs = text.split('\n\n')
    result = []

    for para in paragraphs:
        if not para.strip():
            continue

        # Split by sentences
        sentences = re.split(r'([.!?]+\s+)', para)

        # Reconstruct with sentence delimiters
        current_para = []
        sentence_count = 0

        for i, part in enumerate(sentences):
            current_para.append(part)

            # Check if this is a sentence delimiter
            if re.match(r'[.!?]+\s+', part):
                sentence_count += 1

                # Break paragraph if we hit max sentences
                if sentence_count >= max_sentences and i < len(sentences) - 1:
                    result.append(''.join(current_para).strip())
                    current_para = []
                    sentence_count = 0

        # Add remaining content
        if current_para:
            result.append(''.join(current_para).strip())

    return '\n\n'.join(result)


def _truncate_smartly(text: str, max_length: int) -> str:
    """Truncate text at a natural break point.

    Args:
        text: Input text
        max_length: Maximum length

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    # Try to truncate at sentence boundary
    truncated = text[:max_length]
    last_period = truncated.rfind('.')
    last_exclamation = truncated.rfind('!')
    last_question = truncated.rfind('?')

    last_sentence_end = max(last_period, last_exclamation, last_question)

    if last_sentence_end > max_length * 0.7:  # If we can keep at least 70% of content
        return text[:last_sentence_end + 1].strip()

    # Otherwise, truncate at word boundary
    last_space = truncated.rfind(' ')
    if last_space > 0:
        return text[:last_space].strip()

    # Last resort: hard truncate
    return text[:max_length].strip()


# ============================================================================
# Web Form Formatting
# ============================================================================

def format_for_web_form(response: str) -> str:
    """Format response for web form channel.

    Web form characteristics:
    - Balanced tone (professional but approachable)
    - Medium length (not too long, not too short)
    - Clear structure
    - Can use HTML-like formatting if needed

    Args:
        response: Raw response

    Returns:
        Web form-formatted response
    """
    # Web form is similar to email but slightly more concise
    formatted = response.strip()

    # Ensure proper paragraph spacing
    formatted = re.sub(r'\n{3,}', '\n\n', formatted)

    # Optionally truncate very long responses
    if len(formatted) > 3000:
        formatted = _truncate_smartly(formatted, 2997) + "..."

    return formatted


# ============================================================================
# Helper Functions
# ============================================================================

def strip_markdown(text: str) -> str:
    """Remove markdown formatting from text.

    Args:
        text: Text with markdown

    Returns:
        Plain text
    """
    # Remove bold
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)

    # Remove italic
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)

    # Remove links
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)

    # Remove code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`(.+?)`', r'\1', text)

    # Remove headers
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)

    return text


def add_line_breaks_for_mobile(text: str) -> str:
    """Add line breaks to make text more mobile-friendly.

    Args:
        text: Input text

    Returns:
        Text with mobile-optimized line breaks
    """
    # Break after colons (for lists)
    text = re.sub(r':\s*([A-Z])', r':\n\1', text)

    # Ensure numbered lists have line breaks
    text = re.sub(r'(\d+\.)\s*', r'\n\1 ', text)

    # Clean up multiple line breaks
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def count_sentences(text: str) -> int:
    """Count sentences in text.

    Args:
        text: Input text

    Returns:
        Number of sentences
    """
    sentences = re.split(r'[.!?]+', text)
    return len([s for s in sentences if s.strip()])


def get_response_length_category(text: str) -> str:
    """Categorize response length.

    Args:
        text: Input text

    Returns:
        Category: 'short', 'medium', or 'long'
    """
    length = len(text)

    if length < 200:
        return 'short'
    elif length < 800:
        return 'medium'
    else:
        return 'long'


# ============================================================================
# Validation Functions
# ============================================================================

def validate_response_length(response: str, channel: str) -> bool:
    """Validate that response length is appropriate for channel.

    Args:
        response: Response text
        channel: Communication channel

    Returns:
        True if length is valid, False otherwise
    """
    length = len(response)

    limits = {
        'email': 10000,      # Very generous for email
        'whatsapp': 1600,    # WhatsApp hard limit
        'web_form': 5000     # Reasonable for web forms
    }

    max_length = limits.get(channel, 5000)
    return length <= max_length


def ensure_channel_compliance(response: str, channel: str) -> str:
    """Ensure response complies with channel requirements.

    Args:
        response: Response text
        channel: Communication channel

    Returns:
        Compliant response (truncated if necessary)
    """
    if not validate_response_length(response, channel):
        limits = {
            'email': 10000,
            'whatsapp': 1600,
            'web_form': 5000
        }
        max_length = limits.get(channel, 5000)
        response = _truncate_smartly(response, max_length - 3) + "..."

    return response
