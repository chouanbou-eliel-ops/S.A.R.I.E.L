"""
Tool de consultation Wikipedia pour SARIEL — Phase 2.

Aucune clé API requise. Deux endpoints REST officiels de Wikimedia :
1. /api/rest_v1/page/summary/{titre} — résumé d'un article dont le titre
   exact est connu. Rapide, réponse compacte (champ "extract").
2. /w/rest.php/v1/search/page?q=... — recherche floue, utilisée en repli
   si le titre exact échoue (404), pour retrouver l'article le plus
   probable plutôt que de renvoyer un échec sec au modèle.

Complémentaire à web_search (Tavily) plutôt que redondant : ici, données
structurées et sourcées provenant d'une seule encyclopédie de référence,
pas un résumé agrégé du web générique.
"""

import requests

from tools.base import Tool, ToolSchema, ToolResult, registry

_TIMEOUT_SECONDS = 10
_USER_AGENT = "SARIEL-Assistant/1.0 (projet personnel ; contact non fourni)"
_DEFAULT_LANG = "fr"


def _summary_url(lang: str, title: str) -> str:
    return f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(title)}"


def _search_url(lang: str) -> str:
    return f"https://{lang}.wikipedia.org/w/rest.php/v1/search/page"


def _fetch_summary(lang: str, title: str) -> requests.Response:
    return requests.get(
        _summary_url(lang, title),
        headers={"User-Agent": _USER_AGENT},
        timeout=_TIMEOUT_SECONDS,
    )


def _search_best_match(lang: str, query: str) -> str | None:
    """
    Interroge l'endpoint de recherche pour retrouver le titre exact de
    l'article le plus pertinent. Retourne None si aucun résultat.
    """
    response = requests.get(
        _search_url(lang),
        params={"q": query, "limit": 1},
        headers={"User-Agent": _USER_AGENT},
        timeout=_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    pages = response.json().get("pages", [])
    if not pages:
        return None
    return pages[0].get("key")  # "key" est le titre normalisé exploitable par /page/summary/


def wikipedia_lookup(arguments: dict) -> ToolResult:
    query = arguments.get("query")
    if not query or not isinstance(query, str):
        return ToolResult.fail("Paramètre 'query' manquant ou invalide.")

    lang = arguments.get("lang") or _DEFAULT_LANG
    if not isinstance(lang, str):
        return ToolResult.fail("Paramètre 'lang' invalide (code langue attendu, ex. 'fr').")

    try:
        response = _fetch_summary(lang, query)

        if response.status_code == 404:
            # Titre exact introuvable : on retente via la recherche floue
            # avant d'abandonner, plutôt que de renvoyer un échec direct.
            best_title = _search_best_match(lang, query)
            if best_title is None:
                return ToolResult.ok(
                    f"Aucun article Wikipedia ({lang}) trouvé pour : '{query}'."
                )
            response = _fetch_summary(lang, best_title)

        response.raise_for_status()
        data = response.json()

    except requests.exceptions.Timeout:
        return ToolResult.fail(f"Délai dépassé en interrogeant Wikipedia ({lang}).")
    except requests.exceptions.RequestException as exc:
        return ToolResult.fail(f"Échec de la requête vers Wikipedia : {exc}")
    except ValueError:  # réponse non JSON
        return ToolResult.fail("Réponse de Wikipedia illisible (format inattendu).")

    extract = data.get("extract")
    if not extract:
        return ToolResult.ok(
            f"L'article '{data.get('title', query)}' existe mais ne contient pas de résumé exploitable."
        )

    title = data.get("title", query)
    page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")

    lines = [f"{title}\n", extract]
    if page_url:
        lines.append(f"\nSource : {page_url}")

    return ToolResult.ok("\n".join(lines))


_schema = ToolSchema(
    name="wikipedia_lookup",
    description=(
        "Recherche un résumé encyclopédique fiable et structuré sur Wikipedia "
        "pour un sujet donné. À utiliser pour des faits établis, des définitions, "
        "ou du contexte général sur une personne, un lieu, un concept — "
        "complémentaire à web_search pour de l'information sourcée plutôt "
        "qu'un résumé web générique."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Le sujet ou titre d'article à rechercher, ex. 'Python (langage)'.",
            },
            "lang": {
                "type": "string",
                "description": (
                    "Code langue Wikipedia à interroger, ex. 'fr' ou 'en'. "
                    "Par défaut 'fr' si omis."
                ),
            },
        },
        "required": ["query"],
    },
)

registry.register(Tool(schema=_schema, function=wikipedia_lookup))
