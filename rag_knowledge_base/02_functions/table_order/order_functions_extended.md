---
id: "functions_table_order_extended"
type: "fonction_core"
domaine: "table_order_extended"
langage_proxy: "Progress ABL / OpenEdge"
context: ["action", "result", "order"]
table_abbrev: "ord"
return_type: "String | Logical | Void | Specimen | Report | Diagnosis"
priority: "high"
keywords_fr: ["annuler tous résultats", "liste analyses", "créer rapport", "vérifier analyses demandées", "résultat antérieur", "dossier vide", "demande analyse spécifique", "rapport dossier", "identifier dossier", "service rattaché", "propriétés dossier"]
anti_hallucination: []
tags: [Order, ord, CancelResults, IsRequested, IsEmpty, HasPreviousResults, PropertyList, CreateReport, GetSpecimen, Summary, SetDepartment, GetDiagnosis, ReportList, ToBePhoned, Attribute]
---

# Fonctions étendues de la table Order (Dossier)

Complément de [order_functions.md](order_functions.md) — fonctions avancées.

---

## Attribute
**Signature** : `String Attribute(String AttributeName)`  
Lit un attribut personnalisé du dossier.

```mispl
STRING val;
val := Action.Order().Attribute("MonAttribut");
```

---

## CancelResults
**Signature** : `Logical CancelResults(String PropertyMnemonicList, String Reason)`  
Annule plusieurs résultats du dossier en une seule opération.  
`PropertyMnemonicList` : liste de mnémoniques séparés par virgule.

```mispl
/* Annuler plusieurs analyses d'un coup */
Action.Order().CancelResults("B_PSA,B_PSAL", "Discontinue");
```

---

## IsRequested
**Signature** : `Logical IsRequested(String MnemonicList, Logical All)`  
Teste si une ou plusieurs analyses sont demandées sur le dossier.  
`All = YES` : toutes les analyses de la liste doivent être présentes.

```mispl
/* Vérifier si B_HBA1C est dans le dossier */
IF Action.Order().IsRequested("B_HBA1C", NO) THEN
  Action.Order().AddRequest("B_COMM_HBA1C", ?, ?);
ENDIF;
```

---

## IsEmpty
**Signature** : `Logical IsEmpty()`  
Retourne YES si le dossier ne contient aucune demande.

---

## HasPreviousResults
**Signature** : `Logical HasPreviousResults(String PropertyClassificationName, ResultStatus MinimalResultStatus)`  
Teste si l'objet a des résultats antérieurs pour une classification d'analyses.

---

## PropertyList
**Signature** : `String PropertyList(ResultStatus MinimalStatus, ResultStatus MaximalStatus, String PropertyFieldName, String PropertyClassification, Logical AllowUnsolicitedResults)`  
Retourne la liste des analyses du dossier dans une plage de statuts, formatée en chaîne.

---

## Summary
**Signature** : `String Summary(ResultStatus MinimalStatus, ResultStatus MaximalStatus, String PropertyFieldName, String PropertyClassification, Logical AllowUnsolicitedResults, String Separator)`  
Résumé textuel des résultats du dossier.

---

## GetSpecimen
**Signature** : `Specimen GetSpecimen(Specimen Previous, Mnemonic Material)`  
Itère sur les prélèvements du dossier, filtré par matériau.

```mispl
/* Parcourir les prélèvements */
Specimen spmn;
spmn := Action.Order().GetSpecimen(?, ?);  /* premier prélèvement */
WHILE spmn.Id <> ? DO
  /* traiter spmn */
  spmn := Action.Order().GetSpecimen(spmn, ?);  /* suivant */
DONE;
```

---

## GetDiagnosis
**Signature** : `Diagnosis GetDiagnosis(Diagnosis Previous, String Code)`  
Itère sur les diagnostics du dossier.

---

## CreateReport
**Signature** : `Void CreateReport(String Code)`  
Génère un rapport pour le dossier selon le code de rapport spécifié.

---

## CreateMediumReport
**Signature** : `Void CreateMediumReport(String Code, ReportMedium Medium, String Target, Logical Forced, String GenerationParameterSet, String MediumInfo)`  
Génère un rapport sur un medium spécifié (imprimante, fax, email...).

---

## ReportList
**Signature** : `String ReportList(ReportScope Scope, String DefaultReportCode, Mnemonic TemplateMnemonic, String TargetInternalId, Logical IsCopy)`  
Retourne la liste des rapports disponibles pour le dossier.

---

## SetDepartment
**Signature** : `Logical SetDepartment(Mnemonic DepartmentMnemonic)`  
Modifie la discipline du dossier.

---

## ToBePhoned
**Signature** : `Logical ToBePhoned()`  
Marque le dossier comme "à téléphoner".

---

## HasMissingSpecimens
**Signature** : `Logical HasMissingSpecimens()`  
Retourne YES si le dossier a des prélèvements attendus non encore réceptionnés.

---

## GetIdentifier
**Signature** : `OrderIdentifier GetIdentifier(SiteEnumerated IdentifierType)`  
Retourne un identifiant de dossier selon le type (interne, externe, etc.).

---

## AddOrderTodoItem
**Signature** : `Void AddOrderTodoItem(Mnemonic OrderTodoListMnemonic, String Reason, Date DueDate, String Assignment)`  
Ajoute une tâche à faire au dossier.
