"""Pure helpers for URL query bootstrap and circuit resolution (testable without Streamlit)."""

from __future__ import annotations

from typing import Any, Callable

from ui.circuit_loader import CircuitTemplate, parse_qasm


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
    session[flag] = True
    if not query:
        return None
    return dict(query)


def init_circuit_select_from_query(
    session: dict[str, Any],
    templates: list[CircuitTemplate],
    query_restore: dict[str, Any] | None,
    *,
    widget_key: str = "circuit_select",
) -> None:
    """Seed the circuit selectbox widget key once from a share-link query."""
    if widget_key in session or not query_restore:
        return
    session[widget_key] = circuit_name_from_query(templates, query_restore)


def clear_qasm_state(session: dict[str, Any]) -> None:
    """Reset QASM override when the user picks a different built-in template."""
    session["qasm_text"] = ""
    session["use_qasm_import"] = False


def resolve_active_template(
    template_by_name: dict[str, CircuitTemplate],
    selected_name: str,
    *,
    use_qasm: bool,
    qasm_text: str,
    parser: Callable[[str], CircuitTemplate] = parse_qasm,
) -> tuple[CircuitTemplate, str | None]:
    """
    Return the template to simulate.

    Uses the built-in template unless QASM override is enabled and non-empty.
    Returns an error message string when QASM parsing fails.
    """
    template = template_by_name[selected_name]
    if not use_qasm or not qasm_text.strip():
        return template, None
    try:
        return parser(qasm_text), None
    except ValueError as exc:
        return template, str(exc)