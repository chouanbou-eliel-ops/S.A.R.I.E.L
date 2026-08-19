"""
Tests de tools/safety.py — Phase 2.

Vérifie le filtre statique AST : ce qui doit être bloqué (imports
interdits, appels interdits, contournements évidents) et surtout ce qui
NE DOIT PAS être bloqué (code légitime), pour éviter un filtre trop
agressif qui gênerait l'usage normal de python_exec.
"""

from tools.safety import static_code_check


# ---------------------------------------------------------------------
# Code légitime — ne doit JAMAIS être bloqué (faux positifs)
# ---------------------------------------------------------------------

def test_simple_computation_allowed():
    allowed, reason = static_code_check("print(2 + 2)")
    assert allowed is True
    assert reason is None


def test_math_module_allowed():
    allowed, _ = static_code_check("import math\nprint(math.sqrt(16))")
    assert allowed is True


def test_json_module_allowed():
    allowed, _ = static_code_check("import json\nprint(json.dumps({'a': 1}))")
    assert allowed is True


def test_open_in_read_mode_allowed():
    allowed, _ = static_code_check("f = open('data.txt', 'r')")
    assert allowed is True


def test_open_default_mode_allowed():
    allowed, _ = static_code_check("f = open('data.txt')")
    assert allowed is True


def test_function_definition_allowed():
    code = "def carre(n):\n    return n * n\nprint(carre(7))"
    allowed, _ = static_code_check(code)
    assert allowed is True


def test_syntax_error_not_blocked_by_filter():
    """Une erreur de syntaxe n'est pas du ressort du filtre de sécurité."""
    allowed, reason = static_code_check("def broken(:\n  pass")
    assert allowed is True
    assert reason is None


# ---------------------------------------------------------------------
# Imports interdits
# ---------------------------------------------------------------------

def test_import_os_blocked():
    allowed, reason = static_code_check("import os")
    assert allowed is False
    assert "os" in reason


def test_import_os_submodule_blocked():
    allowed, reason = static_code_check("import os.path")
    assert allowed is False
    assert "os" in reason


def test_from_os_import_blocked():
    allowed, reason = static_code_check("from os import remove")
    assert allowed is False
    assert "os" in reason


def test_import_subprocess_blocked():
    allowed, _ = static_code_check("import subprocess")
    assert allowed is False


def test_import_shutil_blocked():
    allowed, _ = static_code_check("import shutil\nshutil.rmtree('/')")
    assert allowed is False


def test_import_socket_blocked():
    allowed, _ = static_code_check("import socket")
    assert allowed is False


def test_import_requests_blocked():
    allowed, _ = static_code_check("import requests")
    assert allowed is False


def test_import_pathlib_blocked():
    allowed, _ = static_code_check("from pathlib import Path")
    assert allowed is False


def test_import_ctypes_blocked():
    allowed, _ = static_code_check("import ctypes")
    assert allowed is False


def test_import_importlib_blocked():
    allowed, _ = static_code_check("import importlib")
    assert allowed is False


def test_import_urllib_blocked():
    allowed, _ = static_code_check("import urllib.request")
    assert allowed is False


# ---------------------------------------------------------------------
# Appels interdits
# ---------------------------------------------------------------------

def test_eval_blocked():
    allowed, reason = static_code_check("eval('1 + 1')")
    assert allowed is False
    assert "eval" in reason


def test_exec_blocked():
    allowed, _ = static_code_check("exec('print(1)')")
    assert allowed is False


def test_compile_blocked():
    allowed, _ = static_code_check("compile('1+1', '<string>', 'eval')")
    assert allowed is False


def test_dunder_import_call_blocked():
    allowed, _ = static_code_check("__import__('os')")
    assert allowed is False


def test_getattr_blocked():
    allowed, _ = static_code_check("getattr(__builtins__, 'eval')")
    assert allowed is False


def test_globals_blocked():
    allowed, _ = static_code_check("print(globals())")
    assert allowed is False


# ---------------------------------------------------------------------
# Contournements évidents via noms/attributs interdits
# ---------------------------------------------------------------------

def test_builtins_name_reference_blocked():
    allowed, _ = static_code_check("x = __builtins__")
    assert allowed is False


def test_builtins_attribute_access_blocked():
    allowed, _ = static_code_check("x = obj.__builtins__")
    assert allowed is False


# ---------------------------------------------------------------------
# open() en écriture — doit passer par write_file, pas open() natif
# ---------------------------------------------------------------------

def test_open_write_mode_blocked():
    allowed, reason = static_code_check("open('fichier.txt', 'w')")
    assert allowed is False
    assert "open" in reason.lower()


def test_open_append_mode_blocked():
    allowed, _ = static_code_check("open('fichier.txt', 'a')")
    assert allowed is False


def test_open_write_mode_keyword_arg_blocked():
    allowed, _ = static_code_check("open('fichier.txt', mode='w')")
    assert allowed is False


def test_open_dynamic_mode_blocked_by_caution():
    """
    Un mode non littéral (variable) ne peut pas être évalué statiquement
    — le filtre refuse par prudence plutôt que de risquer un faux négatif.
    """
    code = "m = 'w'\nopen('fichier.txt', m)"
    allowed, _ = static_code_check(code)
    assert allowed is False
