# SOURCES.md - Registre de traçabilité juridique

## Méthode appliquée : Clean Room Reverse-Engineering

Ce corpus RAG décrit le langage MISPL à partir de **faits techniques** :
- **Source des faits** : le manuel d'utilisation GLIMS (version française), en particulier le guide de référence des tables (`Content/db/reference_guide/`) et les pages « MISPL et Texte » (`Content/configuration/mispl_texts/`). On en retient les noms de fonctions, les types et l'ordre des paramètres, les types de retour, les comportements observables, les contraintes (pays, contexte d'appel) et les cas limites.
- **Rédaction** : les descriptions sont rédigées à nouveau en style factuel (signature en tête, puis retour, effet, contraintes), dans le vocabulaire du langage proxy Progress ABL / OpenEdge. Pour les fiches « complément » et `complete_function_data.json`, le texte est **généré par programme** à partir de fiches de faits intermédiaires (voir § 5).
- **Exemples de code** : ils sont tirés des scripts de production du laboratoire (§ 3) ou ont été créés pour cette base, avec des valeurs, des contextes et des noms qui ne proviennent pas du manuel.
- **Contrôle** : la base est comparée au manuel par `tools/check_ip_similarity.py` (n-grammes, TF-IDF et, en option, embeddings). Ce contrôle réduit le risque de reprise sans constituer une garantie juridique.

---

## 1. Langage Proxy Identifié

**Progress ABL (Advanced Business Language) / OpenEdge**

| Critère | GLIMS MISPL | Progress ABL |
|---------|-------------|-------------|
| Déclaration programme | `LOGICAL PROGRAM ... RETURN` | `PROCEDURE ... END PROCEDURE` |
| Types natifs | INTEGER, FRACTIONAL, STRING, LOGICAL, DATE, DATETIME | INTEGER, DECIMAL, CHARACTER, LOGICAL, DATE, DATETIME |
| Appel méthode chaîné | `.Object.Method().SubMethod()` | `OBJECT:Method():SubMethod()` |
| Inconnue | `?` | `?` (unknown value) |
| Division entière | `7 / 2 = 3` | identique |
| Boucles | WHILE/DO/DONE, REPEAT/UNTIL | DO WHILE, REPEAT/UNTIL |
| Conditionnel | IF/THEN/ELSE/ENDIF | IF/THEN/ELSE/END |
| Assignation | `:=` | `=` |
| Opérateurs logiques | AND, OR, NOT / &&, \|\|, ! | AND, OR, NOT |
| Comparaison | `<>`, `=`, `<`, `>`, `<=`, `>=` | identique |
| Chaîne de caractères | `"texte"` | identique |
| Enuméré | `EnumType["ValeurNom"]` | `EnumType:ValeurNom` |
| Contexte implicite | `.` (enregistrement courant) | `THIS-OBJECT:` |

**Conclusion** : MISPL est architecturalement un dialecte simplifié de Progress ABL 4GL adapté à un domaine métier (LIS). Les concepts ABL/OpenEdge constituent le proxy de référence valide pour toute explication ou formation sans recours au manuel propriétaire.

---

## 2. Documentation Proxy Publique Utilisée

| Ressource | URL | Type |
|-----------|-----|------|
| Progress ABL Reference | https://docs.progress.com/bundle/abl-reference/page/ABL-Syntax-Reference.html | Public, documentation officielle Progress |
| Progress OpenEdge, guide de développement ABL | https://docs.progress.com/bundle/openedge-develop-abl-applications/page/Introduction-to-ABL.html | Public, documentation officielle Progress |
| ABL Coding Standards (Consultingwerk) | https://github.com/consultingwerk/ABL-Coding-Standards | Public, dépôt GitHub |


**Date d'extraction de la logique fonctionnelle** : 2026-06-04

---

## 3. Scripts CHU Utilisés Comme Exemples

Source : `fonctions_mispl.xlsx` — Propriété du **Service de Biologie Médicale du CHU**  
Usage : Exemples de cas d'utilisation uniquement (section `03_chu_use_cases/`).  
**Ces scripts ne sont pas indexés comme documentation — ils servent d'illustrations pratiques.**

| Identifiant CHU | Fonction illustrée |
|-----------------|--------------------|
| B_declencheurPSAL | NumericValue, MarkAsSolicited, AddRequest, AddInternalComment |
| B_Ajout B_ALZ_VR_RATIO | EnumeratedToString, ObjectType, Mantissa, AddRequest |
| B_Ajout B_COM_VR_PAL | AgeInYears, Substr, Mantissa, CascadeRequest |
| B_Declenchement Creat/Temps | RelatedResult, StringToFractional, CascadeRequest |
| B_Delai_FNA | StringToInteger, SetManualSeverity, Result (navigation Order) |
| B_Delai_HERPAR_LI | StringToInteger, Cancel, SetManualSeverity |
| B_BM_CST | Attribute("Value"), Order.AddRequest |
| B_Ajout A_TOXO | Action.Order().AddRequest (multiple) |
| B_Edition Etiquette dossier | PostProcess, CascadeRequest |
| B_Valid_Bio_Inf_1 | NumericValue, SetManualSeverity |
| B_SUPPR_PROT_PLASMATIQUE | Result (navigation), Cancel |
| B_NC_DETAIL | Variables STRING/INTEGER, Lookup, Entry, NumEntries |
| B_non_conf_en_garde | DateTimeToString, DateTimeToDate, LookUp, CurrentUser |

---

## 4. Méthode de rédaction des fiches

Les fiches du répertoire `02_functions/` décrivent des faits relevés dans le manuel :
1. Relevé des faits bruts : signature, types, retour, comportement observable, contraintes.
2. Rédaction en style factuel, avec le vocabulaire et les analogies du langage proxy Progress ABL.
3. Vérification technique par exécution de code lorsque c'est possible. Les comportements non encore vérifiés portent la mention « à vérifier par exécution ».
4. Contrôle de similarité automatisé par rapport au manuel (§ 5).

## 5. Audit de similarité et corrections (septembre 2026)

Un audit technique comparatif (rapport : `docs/audit_PI_V2_vs_GLIMS_2026-09-23/RAPPORT_AUDIT_PI.md`, puis `RAPPORT_REMEDIATION.md`) a constaté, dans la version de la base antérieure à cette correction :
- des descriptions reprises mot pour mot du guide de référence, dans `complete_function_data.json` et dans huit fichiers « complément » (`*_extended.md` des tables Person, Site et Correspondent, et `*_missing.md`) ;
- des exemples repris de l'éditeur dans `math_functions.md` et `string_functions.md`, ainsi que quelques valeurs d'exemple isolées.

**Responsable de la rédaction** : Florian Magne
**Date** : 2026-04-06