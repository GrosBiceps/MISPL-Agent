# MISPL Agent — Documentation d'ingénierie

Assistant RAG + LLM qui aide les techniciens de laboratoire de biologie
médicale et la DSI d'un laboratoire hospitalier à écrire des scripts MISPL
pour le SIL GLIMS.

Cette documentation couvre les spécifications, l'architecture et les
décisions structurantes, les guides par rôle, le schéma de base de données,
la cartographie du dépôt et la sécurité du projet.

```{toctree}
:maxdepth: 2
:caption: Spécifications

_src_specifications/cahier_des_charges
_src_specifications/acteurs_et_roles
_src_specifications/cas_utilisation
_src_specifications/diagramme_activite
```

```{toctree}
:maxdepth: 2
:caption: Architecture

_src_architecture/architecture
_src_architecture/chronologie
_src_architecture/journal_bugs
```

```{toctree}
:maxdepth: 1
:caption: Décisions d'architecture (ADR)
:glob:

_src_architecture/adr/*
```

```{toctree}
:maxdepth: 2
:caption: Guides

_src_guides/guide_technicien
_src_guides/guide_dsi_administrateur
_src_guides/guide_developpeur
_src_guides/exploitation
```

```{toctree}
:maxdepth: 2
:caption: Base de données
:glob:

_src_base_de_donnees/*
```

```{toctree}
:maxdepth: 2
:caption: Cartographie du dépôt
:glob:

_src_cartographie/*
```

```{toctree}
:maxdepth: 2
:caption: Sécurité
:glob:

_src_securite/*
```

## Autres documents du dépôt

Ces fichiers ne font pas partie de la construction Sphinx (ils vivent hors de
`docs/sphinx/`) ; ils restent lisibles directement sur GitHub, à la racine du
dépôt ou dans `rag_knowledge_base/` :

- `README.md` — présentation générale, installation, démarrage.
- `CHANGELOG.md` — journal des modifications.
- `CLAUDE.md` — règles de travail (anti-hallucination, dépôt public, propriété intellectuelle).
- `rag_knowledge_base/SOURCES.md` — traçabilité de la base de connaissances.
