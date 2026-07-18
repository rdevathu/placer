"""Placer dummy EHR — a lightweight, Epic-like EHR backend for agent development.

The package exposes a FastAPI application (``iliad.main:app``) backed by a single
SQLite database. It is intentionally small: it exists so agents and a demo
frontend can be built against a realistic-but-fake clinical data model.
"""

__version__ = "0.1.0"
