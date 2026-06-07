---
id: "functions_order_navigation"
type: "fonction_core"
domaine: "table_order_navigation"
langage_proxy: "Progress ABL / OpenEdge"
context: ["action", "result", "order"]
table_abbrev: "ord"
return_type: "Logical | String | Specimen | Result | Diagnosis"
priority: "high"
keywords_fr: ["analyse demandée dans dossier", "tester si analyse présente", "naviguer prélèvements", "dossier vide", "antécédents patient", "annuler toutes analyses", "service dossier", "liste analyses dossier", "résumé dossier", "vérifier demandes"]
anti_hallucination: ["IsRequested prend 2 params : String MnemonicList + Logical All"]
tags: [Order, ord, IsRequested, CancelResults, IsEmpty, HasPreviousResults, GetSpecimen, PropertyList, Summary, SetDepartment, ToBePhoned, CreateReport, GetDiagnosis, AddOrderTodoItem]
---

# Navigation et interrogation de la table Order

Complément de [order_functions.md](order_functions.md) et [order_functions_extended.md](order_functions_extended.md).

---

## IsRequested — TEST PRÉSENCE D'ANALYSE CRITIQUE

**Signature** : `Logical IsRequested(String MnemonicList, Logical All)`  
Teste si une ou plusieurs analyses sont présentes sur le dossier courant.  
- `MnemonicList` : liste de mnémoniques séparés par virgule.  
- `All = YES` → toutes les analyses de la liste doivent être présentes.  
- `All = NO` → au moins une suffit.

```mispl
/* Vérifier si une analyse spécifique est dans le dossier */
IF Action.Order().IsRequested("B_HBA1C", NO) THEN
  Action.Order().AddRequest("B_COMM_HBA1C", ?, ?);
ENDIF;

/* Vérifier si TOUTES les analyses d'un panel sont présentes */
IF Action.Order().IsRequested("B_PSA,B_PSAL,B_FPSA", YES) THEN
  Action.Order().AddRequest("B_COMM_PANEL_PSA", ?, ?);
ENDIF;

/* Vérifier si un résultat de contrôle est présent (pattern FNA) */
IF Action.Order().IsRequested("B_COB_LACT_SG", NO) THEN
  .SetManualSeverity(3);
ENDIF;
```

**Alternative** : `.Order.Result("MNEM", ?, ?).Id <> ?` fait la même vérification mais `IsRequested` est plus lisible pour les listes.

---

## CancelResults
**Signature** : `Logical CancelResults(String PropertyMnemonicList, String Reason)`  
Annule un ensemble d'analyses du dossier en une seule opération.

```mispl
/* Annuler un panel complet suite à prélèvement non conforme */
Action.Order().CancelResults("B_PSA,B_PSAL,B_FPSA,B_FPSA_RATIO", "Discontinue");
```

---

## IsEmpty
**Signature** : `Logical IsEmpty()`  
Retourne YES si le dossier ne contient aucune analyse active.

```mispl
IF Action.Order().IsEmpty() THEN
  /* Dossier vide — ne rien déclencher */
  RETURN NO;
ENDIF;
```

---

## HasPreviousResults
**Signature** : `Logical HasPreviousResults(String PropertyClassificationName, ResultStatus MinimalResultStatus)`  
Teste si le patient a des résultats antérieurs validés pour une classification d'analyses.

```mispl
/* Vérifier antécédents avant de déclencher un commentaire */
IF Action.Order().HasPreviousResults("MARQUEURS_TUMORAUX", ?) THEN
  Action.Order().AddRequest("B_COMM_EVOLUTION", ?, ?);
ENDIF;
```

---

## GetSpecimen — ITÉRATION PRÉLÈVEMENTS
**Signature** : `Specimen GetSpecimen(Specimen Previous, Mnemonic Material)`  
Itère sur les prélèvements du dossier. `Previous = ?` pour commencer. `Material = ?` pour tous matériaux.

```mispl
/* Parcourir tous les prélèvements du dossier */
Specimen spmn;
spmn := Action.Order().GetSpecimen(?, ?);
WHILE spmn.Id <> ? DO
  /* traiter chaque prélèvement */
  spmn := Action.Order().GetSpecimen(spmn, ?);
DONE;
```

---

## PropertyList — LISTE DES ANALYSES
**Signature** : `String PropertyList(ResultStatus MinimalStatus, ResultStatus MaximalStatus, String PropertyFieldName, String PropertyClassification, Logical AllowUnsolicitedResults)`  
Retourne la liste CSV des analyses du dossier dans une plage de statuts.

```mispl
/* Obtenir la liste de toutes les analyses actives */
STRING analyses;
analyses := Action.Order().PropertyList(?, ?, "Mnemonic", ?, NO);
/* ex: "B_PSA,B_PSAL,B_NFS,B_CRP" */
```

---

## Summary
**Signature** : `String Summary(ResultStatus MinimalStatus, ResultStatus MaximalStatus, String PropertyFieldName, String PropertyClassification, Logical AllowUnsolicitedResults, String Separator)`  
Résumé textuel formaté des résultats du dossier.

---

## SetDepartment
**Signature** : `Logical SetDepartment(Mnemonic DepartmentMnemonic)`  
Réaffecte le dossier à une autre discipline.

```mispl
/* Transférer à la biochimie */
Action.Order().SetDepartment("BIOCHIMIE");
```

---

## ToBePhoned
**Signature** : `Logical ToBePhoned()`  
Marque le dossier comme "résultat à téléphoner au prescripteur".

```mispl
IF .NumericValue() > 50 THEN
  .Action().Order().ToBePhoned();
  .AddInternalComment("Résultat critique — à téléphoner", YES);
ENDIF;
```

---

## CreateReport
**Signature** : `Void CreateReport(String Code)`  
Génère un rapport pour le dossier selon le code de rapport.

```mispl
Action.Order().CreateReport("RAPPORT_URGENCE");
```
