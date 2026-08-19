"""
Tests de tools/permissions.py — Phase 2.

Vérifie le critère de "done" : "un système de permissions minimal existe :
l'agent ne peut pas, par exemple, supprimer un fichier sans confirmation
explicite." Ici testé via request_confirmation() directement — le lien
avec la boucle agentique (agent.py) est vérifié dans test_agent_permissions.py.

input() est mocké : on ne veut pas que la suite de tests attende une
saisie clavier.
"""

import os
import tempfile
from unittest.mock import patch

import pytest

from tools import permissions


@pytest.fixture
def temp_log():
    """Redirige le fichier de log vers un chemin temporaire pour le test."""
    tmp_path = tempfile.mktemp(suffix=".log")
    with patch.object(permissions, "_LOG_PATH", tmp_path):
        yield tmp_path
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)


@patch("builtins.input", return_value="o")
def test_confirmation_approved(mock_input, temp_log):
    result = permissions.request_confirmation("write_file", {"path": "notes.txt"})
    assert result is True


@patch("builtins.input", return_value="oui")
def test_confirmation_approved_full_word(mock_input, temp_log):
    result = permissions.request_confirmation("write_file", {"path": "notes.txt"})
    assert result is True


@patch("builtins.input", return_value="n")
def test_confirmation_refused(mock_input, temp_log):
    result = permissions.request_confirmation("write_file", {"path": "notes.txt"})
    assert result is False


@patch("builtins.input", return_value="")
def test_confirmation_empty_input_defaults_to_refused(mock_input, temp_log):
    """Aucune réponse ('N' est la valeur par défaut affichée) doit refuser."""
    result = permissions.request_confirmation("write_file", {"path": "notes.txt"})
    assert result is False


@patch("builtins.input", side_effect=KeyboardInterrupt)
def test_confirmation_interrupted_defaults_to_refused(mock_input, temp_log):
    """Ctrl+C pendant la confirmation ne doit jamais approuver par défaut."""
    result = permissions.request_confirmation("write_file", {"path": "notes.txt"})
    assert result is False


@patch("builtins.input", return_value="o")
def test_confirmation_logs_decision(mock_input, temp_log):
    permissions.request_confirmation("write_file", {"path": "notes.txt"})

    assert os.path.exists(temp_log)
    with open(temp_log, "r", encoding="utf-8") as f:
        log_content = f.read()
    assert "APPROUVÉ" in log_content
    assert "write_file" in log_content


@patch("builtins.input", return_value="n")
def test_confirmation_logs_refusal(mock_input, temp_log):
    permissions.request_confirmation("write_file", {"path": "notes.txt"})

    with open(temp_log, "r", encoding="utf-8") as f:
        log_content = f.read()
    assert "REFUSÉ" in log_content
