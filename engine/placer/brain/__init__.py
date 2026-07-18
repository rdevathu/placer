"""The brain: Placer's orchestrator.

Watches the EHR event feed (loop), decides which events matter (watchman),
re-assesses cases with one structured LLM call (gps), plans deterministic work
(router_logic), and exposes the human-decision actions the chat layer calls
(actions). All cross-package imports (workers, chat) are deferred to call time
so the brain loads even while sibling packages are still being built.
"""

from __future__ import annotations
