"""
Tests de tools/file_tools.py — Phase 2.

Vérifie le critère de "done" : "lire ET écrire un fichier sans corrompre
son contenu (écrire, relire, comparer)", ainsi que la contrainte de
sandbox (aucun accès en dehors de data/sandbox/) posée dans docs/secu.md.

Chaque test redirige _SANDBOX_DIR vers un dossier temporaire : on ne veut
pas que la suite de tests touche au vrai data/sandbox/ du projet.
"""

import os
import shutil
import tempfile
from unittest.mock import patch

import pytest

from tools import file_tools


@pytest.fixture
def temp_sandbox():
    """Redirige le sandbox vers un dossier temporaire isolé pour le test."""
    tmp_dir = tempfile.mkdtemp(prefix="sariel_test_sandbox_")
    with patch.object(file_tools, "_SANDBOX_DIR", tmp_dir):
        yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------
# Écriture / lecture — critère "done" principal
# ---------------------------------------------------------------------

def test_write_then_read_roundtrip(temp_sandbox):
    write_result = file_tools.write_file(
        {"path": "notes.txt", "content": "Contenu de test."}
    )
    assert write_result.success is True

    read_result = file_tools.read_file({"path": "notes.txt"})
    assert read_result.success is True
    assert read_result.content == "Contenu de test."


def test_write_creates_subdirectories(temp_sandbox):
    result = file_tools.write_file(
        {"path": "sous_dossier/fichier.txt", "content": "abc"}
    )
    assert result.success is True
    assert os.path.isfile(os.path.join(temp_sandbox, "sous_dossier", "fichier.txt"))


def test_write_overwrites_existing_content(temp_sandbox):
    file_tools.write_file({"path": "notes.txt", "content": "Première version."})
    file_tools.write_file({"path": "notes.txt", "content": "Seconde version."})

    result = file_tools.read_file({"path": "notes.txt"})
    assert result.content == "Seconde version."


def test_read_nonexistent_file(temp_sandbox):
    result = file_tools.read_file({"path": "inexistant.txt"})
    assert result.success is False
    assert "introuvable" in result.error.lower()


def test_read_empty_file(temp_sandbox):
    file_tools.write_file({"path": "vide.txt", "content": ""})
    result = file_tools.read_file({"path": "vide.txt"})
    assert result.success is True
    assert "vide" in result.content.lower()


# ---------------------------------------------------------------------
# Paramètres invalides
# ---------------------------------------------------------------------

def test_read_missing_path_param(temp_sandbox):
    result = file_tools.read_file({})
    assert result.success is False
    assert "path" in result.error


def test_write_missing_content_param(temp_sandbox):
    result = file_tools.write_file({"path": "notes.txt"})
    assert result.success is False
    assert "content" in result.error


# ---------------------------------------------------------------------
# Sandbox — aucun accès en dehors de data/sandbox/ (docs/secu.md)
# ---------------------------------------------------------------------

def test_read_path_traversal_is_blocked(temp_sandbox):
    result = file_tools.read_file({"path": "../../etc/passwd"})
    assert result.success is False
    assert "refusé" in result.error.lower()


def test_write_path_traversal_is_blocked(temp_sandbox):
    result = file_tools.write_file(
        {"path": "../../hors_sandbox.txt", "content": "danger"}
    )
    assert result.success is False
    assert "refusé" in result.error.lower()


def test_write_absolute_path_is_blocked(temp_sandbox):
    result = file_tools.write_file(
        {"path": "/tmp/hors_sandbox.txt", "content": "danger"}
    )
    assert result.success is False
    assert "refusé" in result.error.lower()


# ---------------------------------------------------------------------
# Schémas — vérifie que write_file est bien marqué requires_confirmation
# ---------------------------------------------------------------------

def test_write_file_schema_requires_confirmation():
    from tools.file_tools import _write_schema, _read_schema

    assert _write_schema.requires_confirmation is True
    assert _read_schema.requires_confirmation is False
