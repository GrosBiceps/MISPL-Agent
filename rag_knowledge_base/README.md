# RAG Knowledge Base — MISPL / GLIMS LIS

## Méthode de constitution

Base construite par **rétro-ingénierie Clean Room** :
- Aucun texte verbatim du manuel propriétaire Clinisys/MIPS
- Faits techniques purs (signatures, comportements algorithmiques) rédigés dans le vocabulaire du **langage proxy Progress ABL / OpenEdge**
- Exemples exclusivement issus des scripts de production du laboratoire

Voir [SOURCES.md](SOURCES.md) pour la traçabilité complète.

---

## Arborescence

```
rag_knowledge_base/
├── SOURCES.md                    ← Registre juridique de traçabilité
├── README.md                     ← Ce fichier
├── index_map.json                ← Carte de navigation vectorielle (89 concepts)
├── 01_core_syntax/
│   ├── syntax_overview.md        ← Structure programme, types, opérateurs
│   └── execution_contexts.md     ← Contextes Result/Action/Order, navigation
├── 02_functions/
│   ├── string/
│   │   └── string_functions.md   ← Chr, Substr, Len, Index, Replace, ToUpper... (31 fonctions)
│   ├── conversion/
│   │   └── conversion_functions.md ← StringToFractional, StringToInteger, EnumeratedToString... (8 fonctions)
│   ├── datetime/
│   │   └── datetime_functions.md ← Today, Now, DateTimeToString, AgeInYears... (11 fonctions)
│   ├── misc/
│   │   └── misc_functions.md     ← CurrentUser, PostProcess, SendMail... (23 fonctions)
│   ├── table_result/
│   │   └── result_functions.md   ← NumericValue, Attribute, MarkAsSolicited, Cancel... (12 fonctions)
│   ├── table_order/
│   │   └── order_functions.md    ← AddRequest, CascadeRequest, PostProcess, ScheduleReports...
│   ├── table_action/
│   │   └── action_functions.md   ← ObjectType, Object.AgeInYears, Order()...
│   ├── table_specimen/
│   │   └── specimen_functions.md ← Result, AddRequest, SamplingLocation...
│   └── table_object/
│       └── object_functions.md   ← AgeInYears, BirthDate, Sex...
└── 03_chu_use_cases/
    ├── use_cases_reflex_triggers.md  ← 11 scripts de réflexes analytiques (production)
    └── use_cases_advanced_patterns.md ← 8 patterns avancés + anti-patterns
```

---

## Indexation RAG recommandée

Pour intégrer dans un pipeline ChromaDB + BM25 :

```python
from pathlib import Path

KNOWLEDGE_BASE = Path("rag_knowledge_base")

# Lire tous les .md sauf README et SOURCES
docs = [
    f for f in KNOWLEDGE_BASE.rglob("*.md")
    if f.name not in ("README.md", "SOURCES.md")
]

# Chunk par section H2/H3 (délimiteur "---" ou "##")
# Préserver le frontmatter YAML comme métadonnées
```

---

## Fonctions blacklistées (hallucinations LLM fréquentes)

| Fonction inventée | Remplacement correct |
|-------------------|---------------------|
| `Left(s, n)` | `Substr(s, 1, n)` |
| `Length(s)` | `Len(s)` |
| `LCase(s)` | `ToLower(s)` |
| `UCase(s)` | `ToUpper(s)` |
| `Val(s)` | `StringToFractional(s)` |
| `CInt(s)` | `StringToInteger(s)` |
| `GetValue()` | `NumericValue()` ou `Attribute("Value")` |
| `CreatePerson()` | **IMPOSSIBLE** |
| `StringToReal(s)` | `StringToFractional(s)` |

---

## Statistiques

- **Fonctions documentées** : ~89
- **Scripts CHU** : 19 (57 dans l'xlsx total)
- **Cas d'usage** : 19
- **Fichiers** : 12 fichiers Markdown + 1 JSON
