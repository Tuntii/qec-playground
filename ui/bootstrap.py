"""Pure helpers for one-time URL query bootstrap (testable without Streamlit)."""

from __future__ import annotations

from typing import Any

from ui.circuit_loader import CircuitTemplate


def circuit_name_from_query(
    templates: list[CircuitTemplate],
    query: dict[str, Any],
) -> str:
    """Map a share-link ``circuit`` id to a template display name."""
    circuit_id = query.get("circuit")
    if circuit_id:
        for template in templates:
            if template.id == circuit_id:
                return template.name
    return templates[0].name


def take_query_restore(
    session: dict[str, Any],
    query: dict[str, Any],
    *,
    flag: str = "query_restore",
) -> dict[str, Any] | None:
    """
    Return URL query params exactly once per session.

    Subsequent reruns return None so widgets are not forced back to the URL.
    """
    if session.get(flag):
        return None
    if not query:
        session[flag] = True
        return None
    session[flag] = True
    return dict(query)