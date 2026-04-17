"""Hermes plugin entrypoint for Moonshot/Kimi tools."""

from .tools.kimi_builtin_search import get_builtin_search_registration
from .tools.kimi_formula_tools import get_formula_tool_registrations


def register(ctx) -> None:
    """Register Moonshot/Kimi tools with Hermes via the plugin API."""
    registrations = [get_builtin_search_registration(), *get_formula_tool_registrations()]
    for registration in registrations:
        ctx.register_tool(**registration)
