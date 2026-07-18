"""API routers for the Placer Engine.

Later waves add router modules here (chat.py, cases.py, approvals.py, ...) and
append them to ``routers``; ``main.py`` includes everything in this list. Same
registration pattern as the backend's ``routers/__init__.py``.
"""

from __future__ import annotations

routers: list = []

from .chat import router as chat_router  # noqa: E402

routers.append(chat_router)

from .ops import router as ops_router  # noqa: E402

routers.append(ops_router)
