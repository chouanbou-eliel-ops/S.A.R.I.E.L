"""
Tests de memory.py — vérifient directement le critère de "done" de la
Phase 1 : "La mémoire simple persiste entre deux lancements du script."

On simule deux lancements en créant deux instances distinctes de Memory
pointant vers le même fichier — c'est exactement ce qui se passe entre
deux exécutions réelles de main.py.
"""

import json
import os
import tempfile

import pytest

from memory import Memory


@pytest.fixture
def memory_path():
    """Chemin temporaire unique par test, nettoyé après coup."""
    path = tempfile.mktemp(suffix=".json")
    yield path
    if os.path.exists(path):
        os.unlink(path)


def test_creates_empty_file_on_first_use(memory_path):
    """Un fichier de mémoire inexistant doit être créé automatiquement, vide."""
    assert not os.path.exists(memory_path)
    memory = Memory(memory_path)
    assert os.path.exists(memory_path)
    assert memory.get_all_facts() == []


def test_add_fact_persists_to_disk(memory_path):
    """Un fait ajouté doit être immédiatement lisible dans le fichier JSON brut."""
    memory = Memory(memory_path)
    memory.add_fact("L'utilisateur s'appelle Eliel.")

    with open(memory_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    assert len(raw) == 1
    assert raw[0]["content"] == "L'utilisateur s'appelle Eliel."
    assert "timestamp" in raw[0]


def test_persistence_across_two_instances(memory_path):
    """
    Cœur du critère de Phase 1 : simule deux lancements du script.
    Une première instance ajoute un fait, une seconde (nouvelle, comme
    après un redémarrage) doit le retrouver.
    """
    session_1 = Memory(memory_path)
    session_1.add_fact("Le projet s'appelle SARIEL.")

    # Nouvelle instance = équivalent d'un nouveau lancement de main.py
    session_2 = Memory(memory_path)
    facts = session_2.get_all_facts()

    assert len(facts) == 1
    assert facts[0].content == "Le projet s'appelle SARIEL."


def test_multiple_facts_accumulate_in_order(memory_path):
    """Plusieurs faits ajoutés au fil du temps doivent tous être conservés, dans l'ordre."""
    memory = Memory(memory_path)
    memory.add_fact("Premier fait.")
    memory.add_fact("Deuxième fait.")
    memory.add_fact("Troisième fait.")

    facts = memory.get_all_facts()
    assert [f.content for f in facts] == [
        "Premier fait.",
        "Deuxième fait.",
        "Troisième fait.",
    ]


def test_corrupted_file_does_not_crash(memory_path):
    """
    Un fichier JSON corrompu (ex. coupure de courant en pleine écriture)
    ne doit pas faire planter l'agent au démarrage — on repart d'une
    mémoire vide plutôt que de lever une exception.
    """
    with open(memory_path, "w", encoding="utf-8") as f:
        f.write("{ceci n'est pas du JSON valide")

    memory = Memory(memory_path)
    assert memory.get_all_facts() == []

    # Et l'agent doit pouvoir continuer à écrire normalement après ça
    memory.add_fact("Nouveau départ après corruption.")
    assert len(memory.get_all_facts()) == 1


def test_as_context_string_empty_when_no_facts(memory_path):
    """Sans fait mémorisé, le contexte injecté dans le prompt doit être vide."""
    memory = Memory(memory_path)
    assert memory.as_context_string() == ""


def test_as_context_string_formats_facts_for_prompt(memory_path):
    """Le format de contexte doit être lisible par le LLM et inclure chaque fait."""
    memory = Memory(memory_path)
    memory.add_fact("L'utilisateur est étudiant à l'ENSPY.")

    context = memory.as_context_string()
    assert "L'utilisateur est étudiant à l'ENSPY." in context
    assert "Faits retenus" in context


def test_creates_parent_directory_if_missing(memory_path):
    """Si le dossier parent (ex. data/) n'existe pas encore, il doit être créé."""
    nested_path = os.path.join(tempfile.mkdtemp(), "sous_dossier", "memory.json")
    memory = Memory(nested_path)
    assert os.path.exists(nested_path)
