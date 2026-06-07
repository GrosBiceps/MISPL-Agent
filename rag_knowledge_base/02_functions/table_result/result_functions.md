---
id: "functions_table_result"
type: "fonction_core"
domaine: "table_result"
langage_proxy: "Progress ABL / OpenEdge"
context: ["result"]
table_abbrev: "rslt"
return_type: "Fractional | String | Logical | Result | Action | Specimen | Order"
priority: "critical"
keywords_fr: ["valeur numérique", "valeur résultat", "sévérité", "commentaire interne", "sollicité", "résultat lié", "annuler résultat", "accéder dossier depuis résultat", "marquer", "résultat associé", "valeur brute", "qualificatif", "inconnue", "test si valeur saisie"]
anti_hallucination: ["GetValue n'existe pas → NumericValue() ou Attribute('Value')", "ResultAttribute n'existe pas → Result.Attribute"]
tags: [Result, rslt, NumericValue, Attribute, MarkAsSolicited, SetManualSeverity, RelatedResult, AddInternalComment, Cancel, Mantissa, RawValue, Action, Order, Specimen, Id]
---

# Fonctions de la table Result (Résultat)

Table GLIMS : `rslt` — contient les résultats d'analyses exécutées.  
Dans un contexte MISPL Result, `.` désigne le Result courant.

---

## NumericValue
**Signature** : `Fractional NumericValue()`  
Retourne la valeur numérique du résultat, ou `?` si le résultat n'est pas numérique ou non saisi.  
**Différence avec Mantissa** : `NumericValue()` gère les qualificatifs `<`/`>` (retourne la valeur brute) ; `Mantissa` est le champ de stockage brut.

```mispl
IF .NumericValue() <> ? AND .NumericValue() >= 3.5 AND .NumericValue() < 10 THEN ...
```

---

## Mantissa (champ)
**Type** : `Fractional` — champ direct (pas une méthode).  
Valeur décimale brute du résultat. `<> ?` teste si une valeur a été saisie.

```mispl
IF .Result.Mantissa <> ? THEN ...    /* depuis contexte Action */
IF .Mantissa <> ? THEN ...           /* depuis contexte Result */
```

---

## Attribute / ResultAttribute
**Signature** : `String Attribute(String AttributeName)`  
Lit la valeur d'un champ attribut du résultat sous forme de chaîne.  
`Attribute("Value")` retourne la valeur telle qu'affichée (avec qualificatifs `<`/`>` éventuels).

**Deux formes valides** :
- `.Result.Attribute("Value")` — forme explicite (contexte quelconque)
- `.ResultAttribute("Value")` — forme abrégée raccourcie (contexte Result implicite)

```mispl
STRING valeur;
valeur := .Result.Attribute("Value");    /* forme explicite */
valeur := .ResultAttribute("Value");     /* forme abrégée — équivalente, valide */
/* Ex valeurs : "7.5", "<0.05", "Non", "{O}" */
```

**Insensibilité à la casse** : `Attribute("value")` et `Attribute("Value")` sont identiques.

---

## MarkAsSolicited
**Signature** : `Logical MarkAsSolicited()`  
Marque le résultat courant comme "sollicité" (demandé par réflexe automatique).  
Nécessaire pour tracer les déclenchements automatiques dans le journal d'audit.

```mispl
.MarkAsSolicited();
```

---

## SetManualSeverity
**Signature** : `Logical SetManualSeverity(Integer SeverityCode)`  
Définit manuellement le code de sévérité du résultat (surcharge l'évaluation automatique).  
`SeverityCode = 0` : réinitialise à "normal".

```mispl
.SetManualSeverity(3);    /* sévérité critique */
.SetManualSeverity(0);    /* retour à normal */
```

---

## AddInternalComment
**Signature** : `Logical AddInternalComment(String Comment, Logical Append)`  
Ajoute un commentaire interne au résultat. Si `Append = YES`, concatène au commentaire existant.

```mispl
.AddInternalComment("PSAL déclenché automatiquement", YES);
```

---

## RelatedResult
**Signature** : `Result RelatedResult(String ResultMnemonic)`  
Recherche un autre résultat du même dossier lié à ce résultat.  
Retourne un objet Result (tester `.Id <> ?` pour vérifier l'existence).

```mispl
/* Vérifier qu'un résultat lié existe ET a une valeur */
IF .RelatedResult("B_VOLUME_UR").Id <> ?
  AND StringToFractional(.RelatedResult("B_VOLUME_UR").Attribute("Value")) <> ?
THEN ...
```

---

## Action (navigation)
**Signature** : `Action Action()`  
Remonte à l'Action parente du résultat courant.

```mispl
.Action().Order().AddRequest("MNEM", ?, ?);
.Action().Object.AgeInYears(Today());
```

---

## Order (navigation directe)
**Accès** : `.Order` (propriété directe, sans parenthèses)  
Raccourci vers le dossier (Order) sans passer par l'Action.

```mispl
.Order.AddRequest("B_BM_LEGI", ?, ?);
.Result.Order.AddRequest("B_NON_CONF_CST", ?, ?);
```

---

## Specimen (navigation)
**Accès** : `.Specimen`  
Accède au prélèvement associé au résultat.

```mispl
/* Annuler un résultat sur le prélèvement courant */
.Specimen.Result("B_BM_METH_2230", 1, 5, .Order).Cancel("Discontinue", "Méthode remplacée");
```

---

## Cancel
**Signature** : `Logical Cancel(String Reason, String Comment)`  
Annule le résultat courant avec un code raison et un commentaire explicatif.

```mispl
.Result.Order.Result("B_MOD_PRO_SG", "Initial", "Validated").Cancel("Discontinue", "Remplacé par résultat corrigé");
```

---

## RawValue (champ)
**Type** : `String` — valeur brute non formatée.  
Tester `<> ?` pour vérifier qu'un résultat a une valeur saisie. Plus fiable que `Id` car `Id` peut exister sans valeur.

```mispl
/* Pattern : annuler uniquement si résultat existant ET valeur saisie */
IF .Order.Result("B_MOD_PRO_SG", "Initial", "Validated").RawValue <> ? THEN
  .Order.Result("B_MOD_PRO_SG", "Initial", "Validated")
    .Cancel("Discontinue", "Remplacé par protéine sérique");
ENDIF;
```

---

## Status (champ)
**Type** : `Integer` — code statut du résultat.  
Valeurs numériques courantes (non exhaustif) :

| Valeur | Statut |
|--------|--------|
| 0 | Initial / Non saisi |
| 1 | Saisi |
| 3 | Approuvé |
| 5 | Validé (final) |
| 10 | Annulé |

```mispl
/* Tester si un résultat est déjà validé avant de le recréer */
IF .Result.Order.Result("B_REVUE", ?, ?).Status = 5 THEN
  .Result.Order.Result("B_REVUE", ?, ?).Cancel("Repeat", "Revue à refaire");
ELSE
  .Result.Order.AddRequest("B_REVUE", ?, ?);
ENDIF;
```

---

## Validate
**Signature** : `Logical Validate()`  
Valide le résultat courant (passage au statut validé).  
Utilisé en production dans `B_non_conf_en_garde` pour forcer la validation automatique.

```mispl
/* Validation automatique en mode garde */
Result.SetManualSeverity(600);
Result.validate();    /* valide le résultat automatiquement */
```

```mispl
IF .Order.Result("B_MOD_PRO_SG", "Initial", "Validated").RawValue <> ? THEN ...
```

---

## Cas d'usage CHU — Déclencheur PSA → PSAL

```mispl
/* B_declencheurPSAL : si PSA entre 3.5 et 10, ajouter PSAL */
LOGICAL PROGRAM
  STRING valeur;
  valeur := .Result.Attribute("Value");
  .Result.MarkAsSolicited();
  IF StringToFractional(valeur) >= 3.5 AND StringToFractional(valeur) < 10 THEN
    .Action().Order().AddRequest("PSAL", ?, YES);
    .AddInternalComment("PSAL déclenché automatiquement", YES);
  ENDIF;
RETURN YES;
```

---

## Cas d'usage CHU — Validation avec sévérité conditionnelle

```mispl
/* B_Valid_Bio_Inf_1 : sévérité critique si valeur <= 1 */
LOGICAL PROGRAM
  IF .Result.NumericValue() <= 1 THEN
    .Result.SetManualSeverity(11);
  ELSE
    .Result.SetManualSeverity(0);
  ENDIF;
RETURN YES;
```
