---
id: "functions_result_missing"
type: "fonction_core"
domaine: "result_missing"
langage_proxy: "Progress ABL / OpenEdge"
context: ["result"]
table_abbrev: "rslt"
return_type: "String | Logical | Integer | Object"
priority: "medium"
keywords_fr: ["selection sang resultat", "non-conformite rapportee", "code dilution", "promotion sang", "discontinuation sang"]
anti_hallucination: []
tags: [Result, BloodSelectionDiscontinuation, BloodSelectionPromotion, BloodSelectionReported, GetBloodSelection, GetDilutionCode, ReportedNonconformity]
---

# Fonctions RSLT — complément exhaustif

## BloodSelectionDiscontinuation
**Signature** : `Active Logical Blood Selection Discontinuation(String Reason)`  
Cette fonction permet de discontinuer et répéter la sélection de sang pour lequel le résultat actuel est l'épreuve de compatibilité.  

---

## BloodSelectionPromotion
**Signature** : `Active Logical Blood Selection Promotion()`  

---

## BloodSelectionReported
**Signature** : `Blood Selection Blood Selection Reported()`  

---

## GetBloodSelection
**Signature** : `Blood Selection Get Blood Selection()`  

---

## GetDilutionCode
**Signature** : `Dilution Code Get Dilution Code(String Code)`  
Get dilution code id given a dilution code as stringNeeded in order to be able to dilute a result record using MISPL.  

---

## ReportedNonconformity
**Signature** : `Nonconformity Reported Nonconformity()`  
Needed for reporting: when the report result value contains a text module reference (hence Result-table based) that must be evaluated and the text module wants to access information of the NC record,.  

---
