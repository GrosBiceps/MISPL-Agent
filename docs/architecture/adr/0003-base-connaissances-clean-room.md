# ADR-0003 — Base de connaissances « clean room » en langage proxy ABL, puis remédiation PI

## Statut

Accepté (remédiation appliquée).

## Date

Méthode « clean room » initiale : 2026-06-07 (commit `058c34c`, `feat: MISPL
Agent v2 — base de connaissances manuelle (Clean Room)`). Remédiation de
propriété intellectuelle : 2026-09-24 (commit `584ac55`, `fix(rag): régénère
la base à partir de fiches de faits, supprime les reprises du manuel GLIMS`),
sur la base d'un audit dont le contre-audit date du 2026-09-23.

## Contexte

MISPL n'est documenté que par le manuel propriétaire de l'éditeur GLIMS
(Clinisys/MIPS), non redistribuable et non versionnable dans un dépôt public.
Le projet a besoin d'une base de connaissances qui documente fidèlement les
fonctions MISPL (signature, paramètres, retour, comportement) sans reprendre
l'expression du manuel.

## Décision

Documenter MISPL par une méthode de type **clean room reverse engineering** :
1. Ne retenir du manuel que des **faits techniques** non protégeables en tant
   que tels (noms de fonctions, types et ordre des paramètres, types de
   retour, comportements observables, contraintes).
2. Rédiger ces faits à nouveau, en style factuel, dans le vocabulaire d'un
   **langage proxy public** : Progress ABL / OpenEdge, dont MISPL est un
   dialecte simplifié (architecturalement proche, d'après l'analyse
   consignée dans `rag_knowledge_base/SOURCES.md`), en s'appuyant sur la
   documentation publique de Progress et un dépôt de conventions de codage
   public (`consultingwerk/ABL-Coding-Standards`).
3. Utiliser des exemples de code originaux (scripts de production du
   laboratoire, ou créés pour la base), jamais recopiés du manuel.
4. Contrôler le résultat par un script anti-régression comparant la base au
   manuel (`tools/check_ip_similarity.py`).

**Remédiation de septembre 2026** : un audit de similarité mené le
2026-09-23 a détecté des reprises de l'expression du manuel dans une version
antérieure de la base (281 signalements ÉLEVÉ, 153 MOYEN), notamment dans
`math_functions.md` et `string_functions.md`. La base a été régénérée à
partir de fiches de faits bruts, `complete_function_data.json` et les
fichiers `*_extended.md`/`*_missing.md` ont été réécrits par programme à
partir de ces fiches, et les exemples repris ont été remplacés par des
exemples originaux. Le contre-audit du 2026-09-23 ne relève plus aucun risque
ÉLEVÉ ni MOYEN.

## Alternatives étudiées

- **Citer et résumer le manuel directement** : écarté, car un résumé proche
  reste une reprise de l'expression protégée, en particulier pour un dépôt
  public.
- **Ne documenter que ce que les utilisateurs signalent au fil de l'eau,
  sans base structurée** : écarté, car incompatible avec l'objectif « zéro
  hallucination » — l'agent doit pouvoir dire qu'une fonction n'est pas
  documentée plutôt que de l'inventer, ce qui suppose une base couvrant un
  périmètre large et connu à l'avance.
- **Continuer avec la base d'origine après l'audit** : écarté, le risque de
  reprise étant confirmé et élevé (281 signalements) sur un dépôt public.

## Conséquences

- Toute modification de `rag_knowledge_base/` doit désormais passer par
  `tools/check_ip_similarity.py` avant d'être versionnée (voir
  `docs/specifications/diagramme_activite.md`, second diagramme).
- Le dossier d'audit (`docs/audit_PI_*/`) contient le texte du manuel et
  n'est jamais versionné (exclu par `.gitignore`).
- La traçabilité de la méthode et des sources est documentée dans
  `rag_knowledge_base/SOURCES.md`, qui doit être tenue à jour à chaque
  nouvelle source utilisée.
- Ce contrôle réduit le risque de reprise sans constituer une garantie
  juridique formelle (limite explicitement documentée dans le script et dans
  le `README.md`).
