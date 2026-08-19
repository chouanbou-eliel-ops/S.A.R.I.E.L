"""
Tests de tools/ — vérifient le critère de "done" de la Phase 1 sur la
gestion d'erreur : "si un tool échoue, l'agent ne crash pas, il informe
l'utilisateur."

web_search est testé avec le client Tavily mocké : on ne veut pas que
la suite de tests dépende du réseau ou d'une clé API valide pour tourner.
python_exec et memory_save n'ont pas de dépendance externe, ils sont
testés directement.
"""

import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from tools.base import ToolResult
from tools.python_exec import python_exec
from tools.web_search import web_search
from tools import memory_save as memory_save_module
from memory import Memory


# ---------------------------------------------------------------------
# python_exec
# ---------------------------------------------------------------------

def test_python_exec_success():
    result = python_exec({"code": "print(2 + 2)"})
    assert result.success is True
    assert result.content == "4"


def test_python_exec_missing_code_param():
    result = python_exec({})
    assert result.success is False
    assert "code" in result.error


def test_python_exec_script_error_does_not_fail_tool():
    """
    Une exception DANS le script (ex. division par zéro) n'est pas un
    échec du TOOL lui-même — le tool a bien fonctionné, c'est le code
    utilisateur qui a une erreur. success doit rester True, mais le
    contenu doit rapporter l'erreur au modèle.
    """
    result = python_exec({"code": "1 / 0"})
    assert result.success is True
    assert "ZeroDivisionError" in result.content


def test_python_exec_timeout():
    result = python_exec({"code": "import time; time.sleep(15)"})
    assert result.success is False
    assert "délai" in result.error.lower()


def test_python_exec_empty_output():
    result = python_exec({"code": "x = 1 + 1"})  # pas de print()
    assert result.success is True
    assert "sans sortie" in result.content.lower()


def test_python_exec_multiline_code():
    code = """
def carre(n):
    return n * n

print(carre(7))
"""
    result = python_exec({"code": code})
    assert result.success is True
    assert result.content == "49"


# ---------------------------------------------------------------------
# python_exec — intégration avec le filtre de sécurité (tools/safety.py)
# ---------------------------------------------------------------------

def test_python_exec_blocks_forbidden_import_before_running():
    """
    Vérifie que le code n'est jamais RÉELLEMENT exécuté : si le filtre
    avait échoué à intercepter, ce code supprimerait ce fichier de test
    lui-même (chemin volontairement absurde pour rendre l'effet visible
    en cas de régression : os.remove() n'a aucune chance de s'exécuter
    silencieusement sans qu'un test échoue quelque part).
    """
    result = python_exec({"code": "import os\nos.remove(__file__)"})
    assert result.success is False
    assert "filtre de sécurité" in result.error.lower() or "interdit" in result.error.lower()


def test_python_exec_blocks_eval():
    result = python_exec({"code": "eval('__import__(\"os\").system(\"echo test\")')"})
    assert result.success is False


def test_python_exec_legitimate_code_unaffected_by_filter():
    """Le filtre ne doit pas gêner un usage normal du tool."""
    result = python_exec({"code": "import math\nprint(math.factorial(5))"})
    assert result.success is True
    assert result.content == "120"


# ---------------------------------------------------------------------
# web_search (client Tavily mocké — pas d'appel réseau réel)
# ---------------------------------------------------------------------

def test_web_search_missing_query_param():
    result = web_search({})
    assert result.success is False
    assert "query" in result.error


def test_web_search_missing_api_key():
    """Sans clé API dans l'environnement, le tool doit échouer proprement."""
    with patch.dict(os.environ, {}, clear=True):
        result = web_search({"query": "test"})
    assert result.success is False
    assert "TAVILY_API_KEY" in result.error


@patch("tools.web_search.TavilyClient")
def test_web_search_success(mock_client_class):
    mock_client = MagicMock()
    mock_client.search.return_value = {
        "results": [
            {
                "title": "Titre exemple",
                "content": "Extrait de contenu.",
                "url": "https://example.com",
            }
        ]
    }
    mock_client_class.return_value = mock_client

    with patch.dict(os.environ, {"TAVILY_API_KEY": "fake_key"}):
        result = web_search({"query": "test de recherche"})

    assert result.success is True
    assert "Titre exemple" in result.content
    assert "Extrait de contenu." in result.content


@patch("tools.web_search.TavilyClient")
def test_web_search_no_results(mock_client_class):
    mock_client = MagicMock()
    mock_client.search.return_value = {"results": []}
    mock_client_class.return_value = mock_client

    with patch.dict(os.environ, {"TAVILY_API_KEY": "fake_key"}):
        result = web_search({"query": "requête sans résultat"})

    assert result.success is True
    assert "Aucun résultat" in result.content


@patch("tools.web_search.TavilyClient")
def test_web_search_network_failure_does_not_crash(mock_client_class):
    """
    Critère de gestion d'erreur de la Phase 1 : une panne réseau doit
    être renvoyée comme ToolResult.fail, pas lever d'exception.
    """
    mock_client = MagicMock()
    mock_client.search.side_effect = ConnectionError("Pas de connexion internet")
    mock_client_class.return_value = mock_client

    with patch.dict(os.environ, {"TAVILY_API_KEY": "fake_key"}):
        result = web_search({"query": "test"})

    assert result.success is False
    assert "connexion" in result.content.lower() or "Pas de connexion" in result.error


# ---------------------------------------------------------------------
# memory_save
# ---------------------------------------------------------------------

@pytest.fixture
def bound_memory():
    """Lie une instance de Memory temporaire au tool memory_save pour le test."""
    path = tempfile.mktemp(suffix=".json")
    memory = Memory(path)
    memory_save_module.bind_memory(memory)
    yield memory
    memory_save_module.bind_memory(None)
    if os.path.exists(path):
        os.unlink(path)


def test_memory_save_success(bound_memory):
    result = memory_save_module.memory_save({"content": "Fait important à retenir."})
    assert result.success is True
    assert "Fait important à retenir." in bound_memory.get_all_facts()[0].content


def test_memory_save_missing_content_param(bound_memory):
    result = memory_save_module.memory_save({})
    assert result.success is False
    assert "content" in result.error


def test_memory_save_without_binding_fails_cleanly():
    """Si bind_memory() n'a jamais été appelée, le tool doit échouer proprement."""
    memory_save_module.bind_memory(None)
    result = memory_save_module.memory_save({"content": "test"})
    assert result.success is False
    assert "non initialisée" in result.error


# ---------------------------------------------------------------------
# Registre — vérifie que registry.execute() ne lève jamais d'exception,
# même face à un tool inconnu (garde-fou de plus haut niveau).
# ---------------------------------------------------------------------

def test_registry_unknown_tool_returns_failure_not_exception():
    from tools.base import registry

    result = registry.execute("tool_qui_n_existe_pas", {})
    assert isinstance(result, ToolResult)
    assert result.success is False