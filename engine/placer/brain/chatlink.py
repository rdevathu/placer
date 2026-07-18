"""Deferred bridge to the chat layer (built in parallel by another agent).

``placer.api.chat.post_message`` is the only sanctioned way to put anything in
chat, but that module may not exist yet while the brain is developed/tested —
so the import happens at call time and failure degrades to a logged no-op.
Tests inject a fake ``placer.api.chat`` module into sys.modules.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlmodel import Session

logger = logging.getLogger(__name__)


def post_chat(
    session: Session,
    content: str,
    *,
    case_id: Optional[str] = None,
    kind: str = "text",
    approval_id: Optional[str] = None,
):
    """post_message with a soft dependency; returns the ChatMessage or None."""
    try:
        from placer.api.chat import post_message
    except ImportError:
        logger.warning("placer.api.chat not available; dropping chat message: %s", content[:80])
        return None
    return post_message(session, content, case_id=case_id, kind=kind, approval_id=approval_id)
