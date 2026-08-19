"""
Test d'intégration — vérifie que agent.py respecte bien le flag
requires_confirmation AVANT d'appeler registry.execute().

On ne construit pas d'instance Agent complète (elle appelle l'API
Anthropic réelle dans __init__ via anthropic.Anthropic) : on teste
directement Agent._execute_tool_calls, la méthode qui contient la
logique de permission, avec un faux objet "response" imitant la forme
d'une réponse API contenant un bloc tool_use.

On mocke tools.permissions.request_confirmation plutôt que builtins.input
directement : ce test vérifie le CÂBLAGE agent.py <-> permissions, pas le
comportement interne de permissions.py (déjà couvert par
test_permissions.py).
"""

from dataclasses import dataclass
from typing import Any
from unittest.mock import patch, MagicMock

import pytest

from agent import Agent
from tools.base import Tool, ToolSchema, ToolResult, registry


@dataclass
class _FakeToolUseBlock:
    type: str
    id: str
    name: str
    input: dict


@dataclass
class _FakeResponse:
    content: list


@pytest.fixture
def confirmable_tool():
    """Enregistre un tool factice marqué requires_confirmation=True."""
    calls = []

    def _fn(arguments: dict) -> ToolResult:
        calls.append(arguments)
        return ToolResult.ok("exécuté")

    schema = ToolSchema(
        name="fake_sensitive_tool",
        description="Tool factice pour tester la confirmation.",
        parameters={"type": "object", "properties": {}},
        requires_confirmation=True,
    )
    registry.register(Tool(schema=schema, function=_fn))
    yield "fake_sensitive_tool", calls
    del registry._tools["fake_sensitive_tool"]


@pytest.fixture
def bare_agent():
    """
    Instance Agent sans passer par __init__ (qui exigerait une vraie clé
    API) — on a seulement besoin de la méthode _execute_tool_calls, qui
    ne dépend d'aucun état d'instance.
    """
    return Agent.__new__(Agent)


@patch("agent.permissions.request_confirmation", return_value=True)
def test_confirmed_action_executes_tool(mock_confirm, bare_agent, confirmable_tool):
    tool_name, calls = confirmable_tool
    response = _FakeResponse(
        content=[_FakeToolUseBlock(type="tool_use", id="tu_1", name=tool_name, input={})]
    )

    results = bare_agent._execute_tool_calls(response)

    mock_confirm.assert_called_once_with(tool_name, {})
    assert len(calls) == 1  # le tool a bien été exécuté
    assert results[0]["is_error"] is False


@patch("agent.permissions.request_confirmation", return_value=False)
def test_refused_action_does_not_execute_tool(mock_confirm, bare_agent, confirmable_tool):
    tool_name, calls = confirmable_tool
    response = _FakeResponse(
        content=[_FakeToolUseBlock(type="tool_use", id="tu_1", name=tool_name, input={})]
    )

    results = bare_agent._execute_tool_calls(response)

    mock_confirm.assert_called_once_with(tool_name, {})
    assert len(calls) == 0  # le tool n'a JAMAIS été appelé
    assert results[0]["is_error"] is True
    assert "refusée" in results[0]["content"].lower()


@patch("agent.permissions.request_confirmation")
def test_non_sensitive_tool_skips_confirmation(mock_confirm, bare_agent):
    """python_exec n'a pas requires_confirmation : aucun prompt ne doit apparaître."""
    response = _FakeResponse(
        content=[
            _FakeToolUseBlock(
                type="tool_use", id="tu_1", name="python_exec", input={"code": "print(1)"}
            )
        ]
    )

    results = bare_agent._execute_tool_calls(response)

    mock_confirm.assert_not_called()
    assert results[0]["is_error"] is False
