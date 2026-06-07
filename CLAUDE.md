# MISPL Agent — Règles de Travail Claude

## Mission
Assistant IA spécialisé MISPL/GLIMS pour techniciens de laboratoire de biologie médicale.
Priorités : zéro hallucination, traçabilité documentaire, code MISPL optimisé pour serveur GLIMS.

## Stack
- Python 3.10+, LangChain / LlamaIndex, ChromaDB (vectorstore local)
- Modèle LLM : Claude API (claude-sonnet-4-6) ou modèle local (Ollama/Mistral)
- Embedding : text-embedding-3-small (OpenAI) ou nomic-embed-text (local)
- Documentation source : `french/` — manuel HTML GLIMS complet

## Repository map
- `french/` — documentation GLIMS source (HTML, ne pas modifier)
- `docs/chunks/` — chunks vectorisés (généré par `src/rag/build_vectorstore.py`)
- `src/rag/` — pipeline de chunking et indexation
- `src/agent/` — agent principal + prompts système
- `.claude/skills/` — skills métier MISPL (comportement IA)
- `.claude/rules/` — règles globales agent
- `.claude/agents/` — définitions sous-agents spécialisés
- `outputs/generated_scripts/` — scripts MISPL générés (loggés)
- `tests/mispl_examples/` — exemples validés pour évaluation
- `notebooks/` — exploration et tests RAG

## Règles absolues (Anti-Hallucination)

1. **Ne JAMAIS inventer une fonction MISPL.** Si la fonction n'est pas dans le RAG, répondre :
   > "Aucune documentation trouvée pour cette fonction. Voici du pseudo-code structuré."

2. **Toujours citer** le fichier source et la section utilisée :
   > Source : `Content/configuration/mispl_texts/mispl_table_independent/function_string.htm` — section "Substr"

3. **Qualifier chaque réponse** avec un niveau de certitude :
   - ✅ **Certain** — fonction documentée, syntaxe confirmée
   - ⚠️ **Probable** — inférence depuis documentation partielle
   - 🔬 **À vérifier** — syntaxe non trouvée, pseudo-code fourni

4. **Fallback obligatoire** si syntaxe absente : produire pseudo-code commenté avec structure MISPL valide.

5. **Efficience serveur GLIMS** : préférer les fonctions intégrées aux boucles manuelles, éviter les appels récursifs non nécessaires.

## Format de réponse
```
## Contexte GLIMS
[Rappel bref du contexte métier, 1-2 phrases]

## Code MISPL
[bloc de code]

## Source
[fichier + section documentaire]

## Niveau de certitude
[✅ Certain | ⚠️ Probable | 🔬 À vérifier]

## Notes techniques
[Risques, alternatives, conseils d'optimisation]
```

## Types de données MISPL
- `INTEGER`, `FRACTIONAL`, `STRING`, `LOGICAL`, `DATE`, `DATETIME`, `TIME`
- Valeur inconnue : `?` (UnknownValue) — toujours gérer les cas `?`
- Opérateurs : `+`, `-`, `*`, `/`, `%`, `AND`/`&&`, `OR`/`||`, `NOT`/`!`
- Comparaisons : `EQ`/`=`, `NE`/`<>`, `LT`/`<`, `GT`/`>`, `LE`/`<=`, `GE`/`>=`

## Structures de contrôle MISPL
```mispl
IF condition THEN
  statement;
ELSE
  statement;
ENDIF

WHILE condition DO
  statement;
DONE

REPEAT
  statement;
UNTIL condition
```

## ELN / Contraintes lab (ne pas modifier sans validation biologiste)
- Identifiants échantillons : format site-specific via `DatedIdentifier()` ou `NextValue()`
- Logs obligatoires pour toute modification de résultat : `AddLogEntry()`
- Variables partagées : accès via `GetSiteAttribute()` / `SetSiteAttribute()`
