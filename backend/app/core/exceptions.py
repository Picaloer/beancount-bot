class BeancountBotError(Exception):
    """Base exception"""


class UnsupportedFormatError(BeancountBotError):
    """Bill file format not recognized by any parser"""


class ParseError(BeancountBotError):
    """Failed to parse bill file"""


class ClassificationError(BeancountBotError):
    """Failed to classify transaction"""


class LLMError(BeancountBotError):
    """LLM API call failed"""


class NotFoundError(BeancountBotError):
    """Resource not found"""


class ImportNotFoundError(NotFoundError):
    pass


class TransactionNotFoundError(NotFoundError):
    pass
