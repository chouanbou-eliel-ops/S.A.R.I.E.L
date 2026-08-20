"""
Tests de tools/wikipedia_tool.py — Phase 2.

requests.get est mocké : la suite de tests ne doit dépendre ni du réseau
ni de la disponibilité de Wikipedia (même philosophie que test_web_search
pour Tavily dans test_tools.py).
"""

from unittest.mock import patch, MagicMock

from tools.wikipedia_tool import wikipedia_lookup


def _mock_response(status_code=200, json_data=None):
    """Construit un mock de requests.Response minimal mais suffisant."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    if status_code >= 400:
        import requests
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"{status_code} Error"
        )
    else:
        response.raise_for_status.return_value = None
    return response


# ---------------------------------------------------------------------
# Paramètres invalides
# ---------------------------------------------------------------------

def test_missing_query_param():
    result = wikipedia_lookup({})
    assert result.success is False
    assert "query" in result.error


def test_invalid_lang_param_type():
    result = wikipedia_lookup({"query": "Python", "lang": 123})
    assert result.success is False
    assert "lang" in result.error


# ---------------------------------------------------------------------
# Cas de succès direct (titre exact trouvé du premier coup)
# ---------------------------------------------------------------------

@patch("tools.wikipedia_tool.requests.get")
def test_direct_summary_success(mock_get):
    mock_get.return_value = _mock_response(
        200,
        {
            "title": "Python (langage)",
            "extract": "Python est un langage de programmation interprété.",
            "content_urls": {
                "desktop": {"page": "https://fr.wikipedia.org/wiki/Python_(langage)"}
            },
        },
    )

    result = wikipedia_lookup({"query": "Python (langage)"})

    assert result.success is True
    assert "Python est un langage de programmation interprété." in result.content
    assert "fr.wikipedia.org/wiki/Python_(langage)" in result.content


@patch("tools.wikipedia_tool.requests.get")
def test_default_language_is_french(mock_get):
    mock_get.return_value = _mock_response(200, {"title": "Test", "extract": "Extrait."})

    wikipedia_lookup({"query": "Test"})

    called_url = mock_get.call_args[0][0]
    assert called_url.startswith("https://fr.wikipedia.org/")


@patch("tools.wikipedia_tool.requests.get")
def test_custom_language_used(mock_get):
    mock_get.return_value = _mock_response(200, {"title": "Test", "extract": "Extract."})

    wikipedia_lookup({"query": "Test", "lang": "en"})

    called_url = mock_get.call_args[0][0]
    assert called_url.startswith("https://en.wikipedia.org/")


@patch("tools.wikipedia_tool.requests.get")
def test_summary_without_extract_field(mock_get):
    """Un article existe mais sans champ 'extract' exploitable (ex. page de désambiguïsation)."""
    mock_get.return_value = _mock_response(200, {"title": "Ambiguïté"})

    result = wikipedia_lookup({"query": "Ambiguïté"})

    assert result.success is True
    assert "ne contient pas de résumé" in result.content.lower()


# ---------------------------------------------------------------------
# Repli sur la recherche floue (404 sur le titre exact)
# ---------------------------------------------------------------------

@patch("tools.wikipedia_tool.requests.get")
def test_fallback_to_search_when_exact_title_not_found(mock_get):
    """
    Premier appel (summary direct) → 404.
    Deuxième appel (search) → trouve un titre.
    Troisième appel (summary avec le titre trouvé) → succès.
    """
    not_found = _mock_response(404)
    search_result = _mock_response(200, {"pages": [{"key": "Serpent_python"}]})
    final_summary = _mock_response(
        200, {"title": "Serpent python", "extract": "Famille de serpents."}
    )

    mock_get.side_effect = [not_found, search_result, final_summary]

    result = wikipedia_lookup({"query": "serpent python"})

    assert result.success is True
    assert "Famille de serpents." in result.content
    assert mock_get.call_count == 3


@patch("tools.wikipedia_tool.requests.get")
def test_fallback_search_no_results_returns_clean_message(mock_get):
    not_found = _mock_response(404)
    empty_search = _mock_response(200, {"pages": []})

    mock_get.side_effect = [not_found, empty_search]

    result = wikipedia_lookup({"query": "zzzxxxqqq_inexistant"})

    assert result.success is True  # pas une erreur de tool, juste "rien trouvé"
    assert "aucun article" in result.content.lower()


# ---------------------------------------------------------------------
# Gestion d'erreur — critère de robustesse de la Phase 1, toujours valable
# ---------------------------------------------------------------------

@patch("tools.wikipedia_tool.requests.get")
def test_timeout_does_not_crash(mock_get):
    import requests
    mock_get.side_effect = requests.exceptions.Timeout()

    result = wikipedia_lookup({"query": "Python"})

    assert result.success is False
    assert "délai" in result.error.lower()


@patch("tools.wikipedia_tool.requests.get")
def test_connection_error_does_not_crash(mock_get):
    import requests
    mock_get.side_effect = requests.exceptions.ConnectionError("Pas de réseau")

    result = wikipedia_lookup({"query": "Python"})

    assert result.success is False


@patch("tools.wikipedia_tool.requests.get")
def test_server_error_after_fallback_does_not_crash(mock_get):
    import requests
    server_error = MagicMock()
    server_error.status_code = 500
    server_error.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Error")

    mock_get.return_value = server_error

    result = wikipedia_lookup({"query": "Python"})

    assert result.success is False


@patch("tools.wikipedia_tool.requests.get")
def test_malformed_json_response_does_not_crash(mock_get):
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status.return_value = None
    response.json.side_effect = ValueError("Invalid JSON")
    mock_get.return_value = response

    result = wikipedia_lookup({"query": "Python"})

    assert result.success is False
    assert "illisible" in result.error.lower()


# ---------------------------------------------------------------------
# Schéma — pas de confirmation requise (lecture pure, sans risque)
# ---------------------------------------------------------------------

def test_schema_does_not_require_confirmation():
    from tools.wikipedia_tool import _schema

    assert _schema.requires_confirmation is False
