"""
Interface commune pour tous les tools de SARIEL.

Chaque tool concret (web_search, python_exec, ...) doit :
1. Définir son schéma via `ToolSchema` (nom, description, paramètres).
2. Implémenter une fonction d'exécution respectant la signature `ToolFunction`.
3. S'enregistrer dans le registre via `register_tool`.

Ce fichier ne contient aucune logique métier — uniquement le contrat que
les tools doivent respecter pour être appelables par la boucle agentique
dans agent.py.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List


@dataclass
class ToolResult:
    """
    Résultat normalisé renvoyé par l'exécution d'un tool.

    success=False signale un échec au modèle SANS faire planter le
    programme (critère de gestion d'erreur de la Phase 1). Le champ
    `content` est toujours une chaîne : c'est ce que le modèle va lire.
    """
    success: bool
    content: str
    error: str | None = None

    @staticmethod
    def ok(content: str) -> "ToolResult":
        return ToolResult(success=True, content=content, error=None)

    @staticmethod
    def fail(error_message: str) -> "ToolResult":
        # Le contenu renvoyé au modèle décrit l'échec de façon lisible,
        # pour qu'il puisse informer l'utilisateur ou adapter sa stratégie.
        return ToolResult(
            success=False,
            content=f"Erreur lors de l'exécution du tool : {error_message}",
            error=error_message,
        )


@dataclass
class ToolSchema:
    """
    Description d'un tool au format attendu par l'API du LLM
    (nom, description, schéma JSON des paramètres).

    `requires_confirmation` est lu par agent.py (voir tools/permissions.py) :
    si True, l'agent interrompt la boucle avant exécution et demande une
    confirmation explicite à l'utilisateur. Ce n'est PAS transmis à l'API
    du LLM (absent de to_api_format) — c'est une politique locale, le
    modèle n'a pas à savoir qu'elle existe pour bien fonctionner.
    """
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema standard (type, properties, required)
    requires_confirmation: bool = False

    def to_api_format(self) -> Dict[str, Any]:
        """Convertit le schéma au format attendu par l'API Anthropic."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }


# Signature commune : chaque fonction de tool reçoit un dict d'arguments
# déjà parsés depuis la réponse du modèle, et retourne un ToolResult.
ToolFunction = Callable[[Dict[str, Any]], ToolResult]


@dataclass
class Tool:
    """Regroupe le schéma et la fonction d'exécution d'un tool."""
    schema: ToolSchema
    function: ToolFunction


class ToolRegistry:
    """
    Registre central des tools disponibles pour l'agent.
    agent.py interroge ce registre plutôt que de connaître chaque tool
    individuellement — ajouter un tool en Phase 2 ne touchera pas agent.py.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.schema.name in self._tools:
            raise ValueError(f"Tool déjà enregistré : {tool.schema.name}")
        self._tools[tool.schema.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_schemas(self) -> List[Dict[str, Any]]:
        """Retourne tous les schémas au format API — pour l'appel au LLM."""
        return [tool.schema.to_api_format() for tool in self._tools.values()]

    def execute(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        """
        Exécute un tool par son nom. Ne lève jamais d'exception :
        toute erreur (tool inconnu ou exception interne) devient un
        ToolResult.fail(), conformément au critère de gestion d'erreur.
        """
        tool = self.get(name)
        if tool is None:
            return ToolResult.fail(f"Tool inconnu : '{name}'")

        try:
            return tool.function(arguments)
        except Exception as exc:  # noqa: BLE001 — capture volontairement large
            return ToolResult.fail(f"{type(exc).__name__}: {exc}")


# Instance unique importée par les modules de tools et par agent.py
registry = ToolRegistry()
