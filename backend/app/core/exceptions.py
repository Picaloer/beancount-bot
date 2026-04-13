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


class SkillNotFoundError(BeancountBotError):
    """Named skill directory not found under backend/skills/."""

    def __init__(self, skill_name: str) -> None:
        self.skill_name = skill_name
        super().__init__(f"Skill not found: {skill_name!r}")


class SkillMalformedError(BeancountBotError):
    """Skill directory found but files are missing or invalid."""

    def __init__(self, skill_name: str, detail: str) -> None:
        self.skill_name = skill_name
        self.detail = detail
        super().__init__(f"Skill {skill_name!r} is malformed: {detail}")
