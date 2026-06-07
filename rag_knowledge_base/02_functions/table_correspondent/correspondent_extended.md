---
id: "functions_correspondent_extended"
type: "fonction_core"
domaine: "correspondent_extended"
langage_proxy: "Progress ABL / OpenEdge"
context: ["all"]
table_abbrev: "crsp"
return_type: "String | Logical | Integer | Object"
priority: "low"
keywords_fr: ["entreprise correspondant", "institution correspondant", "identification connue", "liste tournee", "etude correspondant", "montant impaye"]
anti_hallucination: []
tags: [Correspondent, Company, Institution, Organization, KnownIdentification, TourMnemonicList, Study, CreateIdentification, HCProvider, HealthOffice, Budget]
---

# Fonctions CRSP — complément exhaustif

## Budget
**Signature** : `Budget Budget(Mnemonic Budget Class Mnemonic,Invoice Grouping Period Period,Date Validity Date)`  
Cette fonction MISPL récupère l'enregistrement Budget de ce correspondant qui répond aux paramètres spécifiés.  

---

## Company
**Signature** : `Company Company()`  
This function returns the identifier of the company record if the current correspondent is of this type.  

---

## CreateIdentification
**Signature** : `Logical Create Identification(Correspondent Source,String Code,Date Start Date,Date End Date)`  
Creates an identification record for this (target) correspondent.  

---

## HCProvider
**Signature** : `HCProvider HCProvider()`  
Cette fonction récupère l'identifiant de l'enregistrement médecin si le correspondant actuel est de ce type.  

---

## HealthOffice
**Signature** : `Health Office Health Office()`  
Cette fonction récupère l'identifiant de l'enregistrement office de santé si le correspondant actuel est de ce type.  

---

## KnownIdentification
**Signature** : `Identification Known Identification(String External Id,Date Validity Date)`  

---

## Organization
**Signature** : `Organization Organization()`  
Cette fonction récupère l'identifiant de l'enregistrement organisation si le correspondant actuel est de ce type.  

---

## PreviousFinancing
**Signature** : `String Previous Financing(Date Validity Date)`  
Cette fonction cherche le plus récent groupe de dossiers du correspondant.  

---

## Study
**Signature** : `Study Study()`  
Cette fonction récupère l'identifiant de l'enregistrement étude si le correspondant actuel est de ce type.  

---

## TourMnemonicList
**Signature** : `String Tour Mnemonic List(String Pattern)`  
Récupère une liste de mnémoniques, séparés par virgules, des tours auxquels ce correspondant appartient, rangés en fonction du mnémonique de tour.  

---
