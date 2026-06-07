---
id: "functions_table_result_extended"
type: "fonction_core"
domaine: "table_result_extended"
langage_proxy: "Progress ABL / OpenEdge"
context: ["result"]
table_abbrev: "rslt"
return_type: "String | Logical | Result | Fractional"
priority: "high"
keywords_fr: ["valeur de référence", "résultat précédent", "commentaire externe", "résultat antérieur", "successeur", "résultat de base", "validation automatique", "confirmation automatique", "résultat statistique", "priorité résultat", "escalader", "GetCode", "GetPriorResult"]
anti_hallucination: []
tags: [Result, rslt, ReferenceValue, GetPriorResult, PriorAttribute, AddExternalComment, Escalate, SetAsBaseLine, SetAutomaticConfirmation, SetAutomaticValidation, StatisticalWeight, Successor, WorkSpecimen, GetCode, LastOrder, LastRequest]
---

# Fonctions étendues de la table Result

Complément de [result_functions.md](result_functions.md).

---

## AddExternalComment
**Signature** : `Logical AddExternalComment(String Comment, Logical Append)`  
Ajoute un commentaire **externe** (visible sur le rapport) au résultat.  
Différent de `AddInternalComment` (commentaire interne visible uniquement en interne).

```mispl
/* Commentaire visible sur le rapport patient */
.AddExternalComment("Valeur critique — contacter le biologiste", YES);
```

---

## ReferenceValue
**Signature** : `String ReferenceValue()`  
Retourne la valeur de référence (plage normale) appliquée à ce résultat.

```mispl
STRING refval;
refval := .ReferenceValue();
/* ex: "3.5 - 5.0 mmol/L" */
```

---

## GetPriorResult
**Signature** : `Result GetPriorResult(PositiveInteger Index)`  
Retourne le n-ème résultat antérieur pour la même analyse sur le même patient.  
`Index = 1` = le plus récent antérieur.

```mispl
/* Comparer avec le résultat précédent */
Result precedent;
precedent := .GetPriorResult(1);
IF precedent.Id <> ? THEN
  IF .NumericValue() > precedent.NumericValue() * 2 THEN
    .AddInternalComment("Doublement par rapport au résultat précédent", YES);
  ENDIF;
ENDIF;
```

---

## PriorAttribute
**Signature** : `String PriorAttribute(String AttributeName)`  
Lit un attribut du résultat antérieur le plus récent.

```mispl
/* Lire la valeur affichée du résultat précédent */
STRING valPrec;
valPrec := .PriorAttribute("Value");
```

---

## Escalate
**Signature** : `Logical Escalate()`  
Escalade le résultat vers un niveau supérieur de validation/traitement.

```mispl
/* Escalader en cas de valeur critique */
IF .NumericValue() > 500 THEN
  .Escalate();
ENDIF;
```

---

## SetAsBaseLine
**Signature** : `Logical SetAsBaseLine()`  
Marque ce résultat comme valeur de référence personnelle de base pour le patient.

```mispl
/* Définir ce résultat comme référence patient individuelle */
.SetAsBaseLine();
```

---

## SetAutomaticConfirmation
**Signature** : `Logical SetAutomaticConfirmation(Logical Value)`  
Active/désactive la confirmation automatique du résultat (court-circuit de la validation manuelle).

```mispl
.SetAutomaticConfirmation(YES);   /* validation auto activée */
.SetAutomaticConfirmation(NO);    /* retour à validation manuelle */
```

---

## SetAutomaticValidation
**Signature** : `Logical SetAutomaticValidation(Logical Value)`  
Active/désactive la validation automatique du résultat.

```mispl
/* Forcer validation automatique en mode batch */
IF CurrentUser() = ? THEN    /* contexte batch = utilisateur inconnu */
  .SetAutomaticValidation(YES);
ENDIF;
```

---

## StatisticalWeight
**Signature** : `Fractional StatisticalWeight()`  
Retourne le poids statistique du résultat (utilisé pour les calculs de contrôle qualité).

---

## Successor
**Signature** : `Result Successor()`  
Retourne le résultat successeur (le résultat qui a remplacé celui-ci après annulation/correction).

---

## WorkSpecimen
**Signature** : `Specimen WorkSpecimen()`  
Retourne le prélèvement de travail associé à ce résultat.

---

## GetCode
**Signature** : `String GetCode(Mnemonic CodingSystemMnemonic)`  
Retourne le code de résultat selon un système de codage spécifié.

---

## LastOrder
**Signature** : `Order LastOrder(Logical Explicit)`  
Retourne le dernier dossier ayant demandé cette analyse pour le patient.

---

## LastRequest
**Signature** : `Request LastRequest(Logical Explicit)`  
Retourne la dernière demande d'analyse associée.

---

## MicrobiologyAction
**Signature** : `MicrobiologyAction MicrobiologyAction()`  
Accède à l'action microbiologique associée au résultat (si résultat microbiologique).

---

## PathologyExamOfWhichConclusion
**Signature** : `PathologyExam PathologyExamOfWhichConclusion()`  
Retourne l'examen d'anatomopathologie dont ce résultat est la conclusion (si applicable).
