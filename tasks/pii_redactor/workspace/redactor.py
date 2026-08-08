"""PII redactor.

Replaces personally identifiable information in free text with placeholder
tokens. See spec.md for the full contract, token table and worked examples.
"""

from __future__ import annotations


def redact(text: str) -> str:
    """Replace PII in free text with placeholder tokens."""
    raise NotImplementedError
