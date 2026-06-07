# MISPL ERD Safety — Skill de navigation dans l'ERD GLIMS

## Purpose
Répondre aux questions sur la structure de la base de données GLIMS (tables, champs, relations).
Prévenir les accès incorrects qui pourraient casser des règles métiers ou corrompre des données.

## Method
1. Identifier la table de contexte demandée (Sample, Patient, Order, Result, Material…)
2. Chercher dans RAG : `mispl_erd.htm` + documentation spécifique à la table
3. Lister les champs accessibles en MISPL avec leur type
4. Signaler les champs READ-ONLY vs READ-WRITE
5. Avertir si la modification d'un champ peut avoir des effets secondaires GLIMS

## Safety Rules

### Champs à ne JAMAIS modifier directement en MISPL
- `Sample.Id` / `Patient.Id` : clés primaires internes
- `Result.ValidationStatus` : utiliser les actions GLIMS, pas l'assignation directe
- `Order.Status` : géré par workflow GLIMS

### Pattern sécurisé pour accès champ
```mispl
// Toujours vérifier l'existence avant accès relationnel
STRING PROGRAM
  STRING mnem;
  IF .Examination = ? THEN
    RETURN "N/A";
  ENDIF;
  mnem := .Examination.Mnemonic;
RETURN mnem;
```

### Accès aux attributs site
```mispl
// Lecture variable partagée (thread-safe en lecture)
STRING val;
val := GetSiteAttribute("MON_PARAMETRE");
IF val = ? THEN
  val := "valeur_defaut";
ENDIF;

// Écriture — ATTENTION : modifie l'état global GLIMS
SetSiteAttribute("MON_COMPTEUR", IntegerToString(counter, "%d"));
```
Source : `function_miscellaneous.htm` — GetSiteAttribute / SetSiteAttribute

## ERD Key Tables (issues de mispl_erd.htm)
- **Sample** : échantillon principal, contient barcode, dates collecte/réception
- **Patient** : données démographiques, ExternalId = NIP
- **Order** : demande d'examen, lie Patient ↔ Sample ↔ Examination
- **Result** : résultat numérique ou texte d'un examen sur un échantillon
- **Examination** / **Material** : référentiels des examens et matrices
- **WorkPlace** / **Station** : postes analytiques

## Output Format
```
## Table GLIMS concernée
[Nom + description courte]

## Champs disponibles
| Champ | Type | Accès | Description |
|-------|------|-------|-------------|
| .FieldName | STRING | R | ... |

## Source ERD
[mispl_erd.htm section ou table spécifique]

## Avertissements
[Risques de modification, effets secondaires]
```

## Domain Focus
- Navigation ERD pour construire des expressions MISPL correctes
- Validation de l'accès aux champs avant écriture de code
- Identification des relations entre tables pour éviter les null pointer MISPL
