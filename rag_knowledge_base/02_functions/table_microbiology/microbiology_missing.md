---
id: "functions_microbiology_missing"
type: "fonction_core"
domaine: "microbiology_missing"
langage_proxy: "Progress ABL / OpenEdge"
context: ["action", "result"]
table_abbrev: "mcra"
return_type: "String | Logical | Integer | Object"
priority: "medium"
keywords_fr: ["compte tests isolement", "liste stockage isolation", "resultat antibiotique indexe", "sequence isolement", "liste proprietes action", "resultat operation action"]
anti_hallucination: []
tags: [IsolationTestCount, AntibioticResultIndexed, GetStorageList, GetSequence, PropertyList, ResultOperation, SpecimenInput]
---

# Fonctions MCRA + ISOL + ACTN — complément exhaustif

## AntibioticResultIndexed (isol)
**Signature** : `Antibiotic Result Antibiotic Result Indexed(Positive Integer Number)`  
Permet de récupérer le 'n'-ième résultat d'antibiotique d'un isolement.  

---

## ApproachActivity (actn)
**Signature** : `Approach Activity Approach Activity()`  
Retrieve the approach activity (Genetics) linked to this action.  

---

## GetSequence (isol)
**Signature** : `Active Integer Get Sequence(Mnemonic Sequence Type Mnemonic)`  

---

## GetStorageList (isol)
**Signature** : `String Get Storage List()`  

---

## IsolationTestCount (mcra)
**Signature** : `Positive Integer Isolation Test Count(String Organism Mnemonic List,String Test Mnemonic List,Logical Aerobe,String Organism Billing Mark List,Logical Reportable Only,Logical Positive Only,Logical Answered Only)`  
Récupère le nombre de tests d'isolement.  

---

## SpecimenInput (actn)
**Signature** : `Specimen Input Specimen Input()`  

---
