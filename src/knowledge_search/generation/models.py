from enum import StrEnum


class AnswerStatus(StrEnum):
    DISABLED = "disabled"
    GENERATED = "generated"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
