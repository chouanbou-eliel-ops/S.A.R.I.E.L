"""
Mémoire persistante simple pour SARIEL (Phase 1).

Stockage JSON basique : une liste de faits, chacun avec un horodatage.
Aucune recherche sémantique ici — c'est la Phase 3 (mémoire vectorielle)
qui s'en chargera. Pour l'instant, l'agent charge TOUS les faits en
mémoire et les injecte dans le prompt système à chaque requête.

Le fichier est lu/écrit à chaque opération (pas de cache en RAM) pour
garantir qu'un fait ajouté est immédiatement visible si le programme
est relancé — c'est le critère de persistance de la Phase 1.
"""

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class MemoryFact:
    content: str
    timestamp: str  # ISO 8601


class Memory:
    """
    Gère la lecture/écriture du fichier de mémoire JSON.
    Instanciée une fois dans agent.py, avec le chemin fourni par config.py.
    """

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        # Crée le dossier parent (ex. data/) s'il n'existe pas encore,
        # pour que le premier lancement ne plante pas sur un chemin absent.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write([])

    def _read(self) -> list[dict]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # Fichier absent ou corrompu : on repart d'une mémoire vide
            # plutôt que de faire planter l'agent au démarrage.
            return []

    def _write(self, facts: list[dict]) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(facts, f, ensure_ascii=False, indent=2)

    def add_fact(self, content: str) -> MemoryFact:
        """Ajoute un fait et le persiste immédiatement sur disque."""
        fact = MemoryFact(
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        facts = self._read()
        facts.append(asdict(fact))
        self._write(facts)
        return fact

    def get_all_facts(self) -> list[MemoryFact]:
        """Retourne tous les faits mémorisés, du plus ancien au plus récent."""
        return [MemoryFact(**f) for f in self._read()]

    def as_context_string(self) -> str:
        """
        Formate les faits mémorisés pour injection dans le prompt système.
        Retourne une chaîne vide s'il n'y a rien à retenir.
        """
        facts = self.get_all_facts()
        if not facts:
            return ""

        lines = ["Faits retenus des sessions précédentes :"]
        for fact in facts:
            lines.append(f"- {fact.content} (le {fact.timestamp[:10]})")
        return "\n".join(lines)
