---
id: "functions_table_specimen"
type: "fonction_core"
domaine: "table_specimen"
langage_proxy: "Progress ABL / OpenEdge"
context: ["action", "result"]
table_abbrev: "spmn"
return_type: "Result | Logical"
priority: "medium"
keywords_fr: ["prélèvement", "tube", "localisation prélèvement", "annuler depuis prélèvement", "résultat sur prélèvement", "heure prélèvement"]
anti_hallucination: []
tags: [Specimen, spmn, Result, AddRequest, Cancel, SamplingLocation, SamplingTime, Order]
---

# Fonctions de la table Specimen (Prélèvement)

Table GLIMS : `spmn` — représente un prélèvement biologique (tube de sang, urine, LCR...).

---

## Result (navigation)
**Signature** : `Result Result(String Mnemonic, Integer StatusFrom, Integer StatusTo, Order Order)`  
Recherche un résultat sur ce prélèvement.

```mispl
/* Annuler un résultat spécifique sur le prélèvement */
Result.Specimen.Result("B_BM_METH_2230", 1, 5, .Result.Order).Cancel("discontinue", "méthode remplacée");
```

---

## AddRequest (sur Specimen)
**Signature** : `Logical AddRequest(String RequestMnemonic, Logical ToCharge, String BillingMark)`  
Ajoute une demande directement sur le prélèvement.  
**Attention** : signature différente de `Order.AddRequest` — paramètre 2 = `ToCharge` (Logical), pas un Object.

```mispl
/* Ajouter une analyse directement sur le prélèvement */
.Specimen.AddRequest("B_PSA", YES, ?);

/* Depuis contexte Result */
.Result.Specimen.AddRequest("B_CONTROLE", NO, ?);
```

---

## SamplingLocation (champ énuméré)
**Type** : `Enumerated (SamplingLocation)`  
Type de localisation du prélèvement (bras gauche, bras droit, cathéter...).  
Convertir avec `EnumeratedToString("SamplingLocation", .SamplingLocation)`.

```mispl
STRING loc;
loc := EnumeratedToString("SamplingLocation", .Specimen.SamplingLocation);
/* ex: "LeftArm", "RightArm", "CentralLine" */
```

---

## SamplingTime (champ)
**Type** : `DateTime`  
Horodatage du prélèvement.

```mispl
/* Calculer le délai depuis le prélèvement */
FRACTIONAL heures;
heures := (DateTimeToTime(Now()) - DateTimeToTime(.Specimen.SamplingTime)) / 3600.0;
IF heures > 4 THEN
  .AddInternalComment("Délai prélèvement > 4h", YES);
ENDIF;
```

---

## Order (navigation)
**Accès** : `.Specimen.Order` ou navigation inverse depuis Result.

```mispl
/* Accéder au dossier depuis un prélèvement */
.Specimen.Order.AddRequest("B_CONTROLE", ?, ?);
```

---

## Cas d'usage CHU — Annulation d'un résultat par mnémonique sur prélèvement

```mispl
/* B_BM_DSC_METH_2230 : annuler la méthode 2230 remplacée par 2226 */
LOGICAL PROGRAM
  Result.Specimen.Result("B_BM_METH_2230", 1, 5, .Result.Order)
    .Cancel("discontinue", "méthode 2226 remplace méthode 2230");
RETURN YES;
```
