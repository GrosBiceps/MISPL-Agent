# SOURCES.md - Registre de traçabilité juridique

## Méthode appliquée : Clean Room Reverse-Engineering

Ce corpus RAG a été constitué exclusivement par **rétro-ingénierie fonctionnelle** :
- Les **signatures techniques** (nom, paramètres, types) sont des **faits informatiques purs**, non protégeables en tant que tels.
- Les **descriptions** sont entièrement réécrites dans le vocabulaire du langage proxy (Progress ABL / OpenEdge).
- Les **exemples de code** proviennent uniquement des scripts de production du laboratoire (propriété du service de biologie médicale du CHU).
- **Aucun texte verbatim** du manuel d'origine n'a été reproduit.

---

## 1. Langage Proxy Identifié

**Progress ABL (Advanced Business Language) / OpenEdge**

| Critère | GLIMS MISPL | Progress ABL |
|---------|-------------|-------------|
| Déclaration programme | `LOGICAL PROGRAM ... RETURN` | `PROCEDURE ... END PROCEDURE` |
| Types natifs | INTEGER, FRACTIONAL, STRING, LOGICAL, DATE, DATETIME | INTEGER, DECIMAL, CHARACTER, LOGICAL, DATE, DATETIME |
| Appel méthode chaîné | `.Object.Method().SubMethod()` | `OBJECT:Method():SubMethod()` |
| Inconnue | `?` | `?` (unknown value) |
| Division entière | `321 / 60 = 5` | identique |
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

## 4. Déclaration de non-plagiat

Les fiches du répertoire `02_functions/` ont été rédigées selon la méthode **Clean Room** :
1. Extraction des faits bruts (signature, comportement algorithmique) depuis le manuel source retapé à la main.
2. **Destruction immédiate** de la formulation textuelle originale.
3. Rédaction entièrement nouvelle basée sur les analogies Progress ABL et l'algorithmie standard.
4. Validation par expertise technique (exécution du code), non par comparaison avec le manuel.

**Responsable de la rédaction** : Florian Magne — florian.magne@chu-limoges.fr 
**Date** : 2026-04-06