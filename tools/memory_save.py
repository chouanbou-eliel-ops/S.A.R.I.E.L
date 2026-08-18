"""
Tool de mémorisation pour SARIEL.

Permet au LLM d'enregistrer, de sa propre initiative, un fait qu'il juge
utile de retenir pour les sessions futures (préférence de l'utilisateur,
information personnelle, décision prise en cours de route, etc.).

Ce tool a besoin d'une instance de Memory pour fonctionner — contrairement
à web_search et python_exec qui sont sans état, celui-ci doit écrire sur
le même fichier que le reste de l'agent. L'instance est injectée via
`bind_memory()`, appelée une seule fois par agent.py au démarrage.
"""

from tools.base import Tool, ToolSchema, ToolResult, registry

_memory_instance = None  # injecté par bind_memory()


def bind_memory(memory_instance) -> None:
    """
    Associe l'instance de Memory partagée au tool. Doit être appelée une
    fois au démarrage de l'agent, avant tout appel du tool memory_save.
    """
    global _memory_instance
    _memory_instance = memory_instance


def memory_save(arguments: dict) -> ToolResult:
    """Enregistre un fait dans la mémoire persistante."""
    if _memory_instance is None:
        return ToolResult.fail(
            "Mémoire non initialisée — bind_memory() n'a pas été appelée."
        )

    content = arguments.get("content")
    if not content or not isinstance(content, str):
        return ToolResult.fail("Paramètre 'content' manquant ou invalide.")

    fact = _memory_instance.add_fact(content)
    return ToolResult.ok(f"Fait mémorisé avec succès : « {fact.content} »")


_schema = ToolSchema(
    name="memory_save",
    description=(
        "Enregistre durablement un fait important pour les sessions futures : "
        "une préférence exprimée par l'utilisateur, une information personnelle "
        "qu'il partage, ou une décision prise pendant la conversation. "
        "N'utilise ce tool que pour des faits réellement utiles à retenir sur "
        "le long terme, pas pour des détails triviaux ou temporaires."
    ),
    parameters={
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "Le fait à mémoriser, formulé de façon claire et autonome.",
            }
        },
        "required": ["content"],
    },
)

registry.register(Tool(schema=_schema, function=memory_save))
