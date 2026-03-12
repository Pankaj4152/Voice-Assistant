"""
intent/exceptions.py
─────────────────────
Custom exceptions for the Intent module.
Each exception gives a clear fix message — no more cryptic errors!
"""


class IntentError(Exception):
    """Base exception for all intent-related errors."""
    pass


class APIKeyMissingError(IntentError):
    """Raised when GEMINI_API_KEY is not set."""

    def __init__(self):
        super().__init__(
            "\n\n[APIKeyMissingError] GEMINI_API_KEY is not set!\n"
            "Fix:\n"
            "  1. Create a .env file in your project root\n"
            "  2. Add this line: GEMINI_API_KEY=your-key-here\n"
            "  3. Get your key at: https://aistudio.google.com/app/apikey\n"
        )


class APIRequestError(IntentError):
    """Raised when Gemini API request fails."""

    def __init__(self, reason: str):
        super().__init__(
            f"\n\n[APIRequestError] Gemini API request failed.\n"
            f"Reason: {reason}\n"
            f"Fix: Check your API key, internet connection, or quota.\n"
        )


class ClassificationTimeoutError(IntentError):
    """Raised when Gemini API takes too long."""

    def __init__(self, timeout: int):
        super().__init__(
            f"\n\n[ClassificationTimeoutError] Gemini timed out after {timeout}s.\n"
            f"Fix: Check your internet connection or increase timeout in config.py\n"
        )


class EmptyInputError(IntentError):
    """Raised when input text is empty or whitespace only."""

    def __init__(self):
        super().__init__(
            "[EmptyInputError] Input text is empty. "
            "Please provide a non-empty voice command."
        )