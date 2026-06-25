"""Pure helpers for URL query bootstrap and schedule resolution (testable without Streamlit)."""

from __future__ import annotations

from typing import Any

from ui.schedule_loader import ScheduleTemplate


def schedule_name_from_query(
    templates: list[ScheduleTemplate],
    query: dict[str, Any],
) -> str:
    """Map a share-link ``schedule`` id to a template display name."""
    schedule_id = query.get("schedule") or query.get("circuit")
    if schedule_id:
        for template in templates:
            if template.id == schedule_id:
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
    session[flag] = True
    if not query:
        return None
    return dict(query)


def init_schedule_select_from_query(
    session: dict[str, Any],
    templates: list[ScheduleTemplate],
    query_restore: dict[str, Any] | None,
    *,
    widget_key: str = "schedule_select",
) -> None:
    """Seed the schedule selectbox widget key once from a share-link query."""
    if widget_key in session or not query_restore:
        return
    session[widget_key] = schedule_name_from_query(templates, query_restore)