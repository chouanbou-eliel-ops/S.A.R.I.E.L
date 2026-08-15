# SARIEL
**S**ystem for **A**dvanced **R**esearch & **I**ntelligent **E**xecution **L**ogic

Assistant IA personnel type "Jarvis" : un noyau agentique unique (LLM + tools + mémoire) sur lequel viennent se brancher différentes interfaces (texte, voix, domotique, dashboard) au fil des phases du projet, plutôt qu'un système reconstruit à chaque nouvelle capacité.

Projet personnel réalisé en solo, en parallèle des études (Licence Sciences de l'Ingénieur, option Informatique, ENSPY), dans une optique double : apprentissage technique en profondeur (function calling brut, mémoire vectorielle, pipeline vocal) et constitution d'une pièce de portfolio pour candidature en Master Data & AI.

## Roadmap

| Phase | Contenu | Statut |
|-------|---------|--------|
| 1 | Noyau agentique en texte (CLI, 2 tools, mémoire simple) | 🔄 En cours |
| 2 | Outils étendus (fichiers, API externes, permissions) | ⏳ |
| 3 | Mémoire long terme (recherche vectorielle) | ⏳ |
| 4 | Couche vocale (STT/TTS) | ⏳ |
| 5 | Wake word + écoute continue | ⏳ |
| 6 | Domotique (Home Assistant, simulation ou réel) | ⏳ |
| 7 | Dashboard web unifié | ⏳ |

Critères de "done" détaillés pour chaque phase : voir [`docs/phase_criteria.md`](docs/phase_criteria.md).

## Structure du projet

```
sariel/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── main.py            # point d'entrée CLI
├── agent.py           # boucle de function calling
├── config.py           # chargement config/env
├── memory.py           # persistance JSON/SQLite
├── tools/
│   ├── base.py          # interface commune des tools
│   ├── web_search.py
│   └── python_exec.py
├── data/               # mémoire persistée (ignoré par git)
├── tests/
└── docs/
    └── phase_criteria.md
```

## Installation

```bash
python -m venv venv
source venv/bin/activate   # Windows : venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # puis renseigner la clé API
```

## Utilisation (Phase 1)

```bash
python main.py
```

## Choix techniques (Phase 1)

- **LLM :** _(à trancher — voir historique des décisions dans `docs/phase_criteria.md`)_
- **Mémoire :** JSON/SQLite en Phase 1, migration vers Chroma/FAISS en Phase 3
- **Langage :** Python 3.11+

## Licence

Projet personnel, non destiné à la distribution en l'état.
