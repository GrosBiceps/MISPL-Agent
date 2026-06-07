---
id: "functions_person_extended"
type: "fonction_core"
domaine: "person_extended"
langage_proxy: "Progress ABL / OpenEdge"
context: ["all"]
table_abbrev: "prsn"
return_type: "String | Logical | Integer | Object"
priority: "medium"
keywords_fr: ["anticorps HLA", "antigene HLA", "groupage sanguin", "phenotype rhesus", "sejours patient", "dossier medical", "conseil typage", "liens familiaux"]
anti_hallucination: []
tags: [Person, HLAAntibody, HLAAntigen, RhesusPhenoType, GetEncountersList, GetMedicalRecord, SetMedicalRecord, SetHLAAntigenPresence, OtherAntigens, Stays, RelationsOverview, AfterBirth]
---

# Fonctions PRSN — complément exhaustif

## AfterBirth
**Signature** : `Person After Birth()`  
En cas d'une personne 'foetus' qui après la naissance est également enregistrée dans GLIMS comme une personne 'née' (faisant référence au foetus), cette fonction MISPL permet de naviguer à la personne.  

---

## AntigenAntibody
**Signature** : `Person Antigen Antigen Antibody(Mnemonic Antigen Mnemonic)`  
Récupère l'identifiant de l'enregistrement indiquant la présence ou l'absence (chez la personne) d'un antigène spécifié.  

---

## AntigenByNumber
**Signature** : `Person Antigen Antigen By Number(Positive Integer Number)`  
Récupère le n-ième enregistrement antigène de la personne, où 'n' est le paramètre.  

---

## AvailableBloodBagByNumber
**Signature** : `Blood Bag Available Blood Bag By Number(Mnemonic Product Mnemonic,Logical Autologous,Blood Bag Status Status,Positive Integer Number)`  
Récupère la n-ième poche de sang actuellement disponible (état 'initial') pour cette personne.  

---

## BloodForPersonAvailable
**Signature** : `Logical Blood For Person Available(Mnemonic Product Mnemonic,Logical Autologous,Mnemonic Department Mnemonic,Blood Bag Status Status)`  
Récupère TRUE quand au moins une poche de sang est disponible (état 'Initial') pour la personne.  

---

## CalculateMedidocCaseNumber
**Signature** : `String Calculate Medidoc Case Number()`  
Fonction MISPL qui calcule le numéro medidoc du patient.  

---

## GetAntibody
**Signature** : `Logical Get Antibody(String Antigen Mnemonic)`  

---

## GetEncountersList
**Signature** : `String Get Encounters List()`  
This returns a list of all open Person Encounters.  

---

## GetMedicalRecord
**Signature** : `Person Medical Record Get Medical Record()`  

---

## GetTypingAdvice
**Signature** : `Logical Get Typing Advice(String Blood Bag Internal Id,String Antigen Mnemonic)`  
Cette fonction MISPL pourrait servir à consulter d'éventuel conseil pour la transfusion.  

---

## HLAAntibody
**Signature** : `Person HLAAntibody HLAAntibody(Mnemonic Antibody Mnemonic)`  
Récupère l'enregistrement anticorps HLA de la personne pour un anticorps spécifié.  

---

## HLAAntibodyByNumber
**Signature** : `Person HLAAntibody HLAAntibody By Number(Positive Integer Number)`  
Récupère le n-ième enregistrement anticorps HLA de la personne, où 'n' sert de paramètre.  

---

## HLAAntigen
**Signature** : `Person HLAAntigen HLAAntigen(Mnemonic Antigen Mnemonic)`  
Récupère l'enregistrement antigène HLA de la personne pour l'antigène spécifié.  

---

## HLAAntigenByNumber
**Signature** : `Person HLAAntigen HLAAntigen By Number(Positive Integer Number)`  
Récupère le n-ième enregistrement antigène HLA de la personne, où 'n' sert de paramètre.  

---

## OtherAntigens
**Signature** : `String Other Antigens()`  
Deux fonctions MISPL sont disponibles sur la table Personne: RhesusPhenoType & OtherAntigens.  

---

## RelationsOverview
**Signature** : `String Relations Overview(Mnemonic Text Mnemonic,String Type,Logical Recursive)`  
Récupère un texte rédigé en répétant le module de texte spécifié (basé sur 'Person') pour chaque personne apparentée à la personne originale.  

---

## RhesusPhenoType
**Signature** : `String Rhesus Pheno Type()`  
Deux fonctions MISPL sont disponibles sur la table Personne: RhesusPhenoType & OtherAntigens.  

---

## SetAntibody
**Signature** : `Active Logical Set Antibody(String Antigen Mnemonic,Logical Presence)`  
Afin de prendre en compte les anticorps d'une personne lors d'une transfusion, il est nécessaire de pouvoir les stocker.  

---

## SetHLAAntibodyPresence
**Signature** : `Active Logical Set HLAAntibody Presence(Mnemonic Antibody Name,Date The Date,Logical Presence)`  

---

## SetHLAAntibodyRValue
**Signature** : `Active Logical Set HLAAntibody RValue(Mnemonic Antibody Name,Date The Date,Positive Fractional RValue)`  

---

## SetHLAAntigenPresence
**Signature** : `Active Logical Set HLAAntigen Presence(Mnemonic Antigen Name,Logical Presence)`  
Définir la présence (YES) ou l'absence (NO) de l'antigène HLA spécifié ou l'effacer en spécifiant '?' pour le paramètre 'Presence'.  

---

## SetMedicalRecord
**Signature** : `Active Logical Set Medical Record(String Field Name,String Field Value)`  
Permet de renseigner ou modifier les champs du dossier médical d'une personne.  

---

## SetTypingAdvice
**Signature** : `Active Logical Set Typing Advice(Mnemonic Antigen Mnemonic,Logical Value)`  
Met le champ 'Avis de typage' au niveau de la table 'Antigène personne' à la valeur spécifiée (pour cette personne et cet antigène).  

---

## Stays
**Signature** : `String Stays()`  
This returns a String list of all open Stays of a Person.  

---
