"""
Tool de recherche web pour SARIEL, basé sur l'API Tavily.

Documentation : https://docs.tavily.com/sdk/python/quick-start
"""

import os

from tavily import TavilyClient

from tools.base import Tool, ToolSchema, ToolResult, registry

_MAX_RESULTS = 5


def _get_client() -> TavilyClient:
    """
    Instancie le client Tavily à la demande (pas au chargement du module)
    pour que l'absence de clé API ne fasse planter que l'appel du tool,
    pas l'import du programme entier.
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError(
            "TAVILY_API_KEY absente de l'environnement. "
            "Vérifiez votre fichier .env."
        )
    return TavilyClient(api_key=api_key)


def web_search(arguments: dict) -> ToolResult:
    """
    Exécute une recherche web et renvoie un résumé texte des meilleurs
    résultats, prêt à être lu par le modèle.
    """
    query = arguments.get("query")
    if not query or not isinstance(query, str):
        return ToolResult.fail("Paramètre 'query' manquant ou invalide.")

    try:
        client = _get_client()
        response = client.search(query=query, max_results=_MAX_RESULTS)
    except Exception as exc:  # noqa: BLE001 — réseau, clé invalide, timeout, etc.
        return ToolResult.fail(f"Échec de la recherche web : {exc}")

    results = response.get("results", [])
    if not results:
        return ToolResult.ok(f"Aucun résultat trouvé pour la requête : '{query}'.")

    # Formatage compact — titre + extrait + source, lisible par le modèle
    lines = [f"Résultats de recherche pour : '{query}'\n"]
    for i, result in enumerate(results, start=1):
        title = result.get("title", "Sans titre")
        content = result.get("content", "")
        url = result.get("url", "")
        lines.append(f"{i}. {title}\n   {content}\n   Source : {url}\n")

    return ToolResult.ok("\n".join(lines))


_schema = ToolSchema(
    name="web_search",
    description=(
        "Recherche des informations actuelles sur le web. À utiliser pour "
        "toute question portant sur des faits récents, des données que le "
        "modèle ne connaît pas avec certitude, ou nécessitant une vérification."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "La requête de recherche, concise et ciblée.",
            }
        },
        "required": ["query"],
    },
)

registry.register(Tool(schema=_schema, function=web_search))
