---
id: "functions_table_specimen_extended"
type: "fonction_core"
domaine: "table_specimen_extended"
langage_proxy: "Progress ABL / OpenEdge"
context: ["action", "result"]
table_abbrev: "spmn"
return_type: "String | Logical | Result | Specimen | PathologyExam"
priority: "medium"
keywords_fr: ["prélèvement taille", "stockage prélèvement", "premier résultat prélèvement", "comptage porteurs", "attribut prélèvement", "informations collecte", "prélèvement parent", "taille mesurée", "sortie prélèvement"]
anti_hallucination: []
tags: [Specimen, spmn, Attribute, GetStorage, SetStorage, FirstRequest, LastRequest, CarrierCount, IsolationCount, PathologyExam, CollectionInfo, DirectParent, SetMeasuredSize, LabSpecificSize, Variable]
---

# Fonctions étendues de la table Specimen (Prélèvement)

Complément de [specimen_functions.md](specimen_functions.md).

---

## Attribute
**Signature** : `String Attribute(String AttributeName)`  
Lit un attribut du prélèvement.

---

## FirstRequest / LastRequest
**Signatures** :
```
Request FirstRequest(Logical Explicit)
Request LastRequest(Logical Explicit)
```
Retourne la première/dernière demande liée à ce prélèvement.

---

## CollectionInfo
**Signature** : `String CollectionInfo()`  
Retourne les informations de collecte du prélèvement (heure, localisation, etc.).

---

## DirectParent
**Signature** : `Specimen DirectParent()`  
Retourne le prélèvement parent direct (dans une hiérarchie de prélèvements).

---

## GetStorage / SetStorage
**Signatures** :
```
ItemStorage GetStorage(Mnemonic ArchiveMnemonic, String Usage)
Void SetStorage(Logical Override, String ArchiveMnemonic, String Usage, String CodePattern, String Reason)
```
Lit/définit le lieu de stockage (archivage) du prélèvement.

---

## LabSpecificSize
**Signature** : `String LabSpecificSize()`  
Retourne la taille spécifique au laboratoire pour ce prélèvement.

---

## SetMeasuredSize
**Signature** : `Logical SetMeasuredSize(Fractional Size)`  
Définit la taille/volume mesuré du prélèvement.

---

## CarrierCount
**Signature** : `PositiveInteger CarrierCount()`  
Retourne le nombre de porteurs (carriers) associés au prélèvement.

---

## IsolationCount
**Signature** : `PositiveInteger IsolationCount()`  
Retourne le nombre d'isolements microbiologiques sur ce prélèvement.

---

## PathologyExam
**Signature** : `PathologyExam PathologyExam()`  
Accède à l'examen d'anatomopathologie associé.

---

## AddCarriers
**Signature** : `Logical AddCarriers(String MnemonicList, Logical Print, Logical MarkAsGrafted, Logical Double, String Comment)`  
Ajoute des milieux de culture (carriers) au prélèvement.

---

## Variable
**Signature** : `String Variable(Mnemonic VariableMnemonic)`  
Lit la valeur d'une variable de prélèvement configurée.
