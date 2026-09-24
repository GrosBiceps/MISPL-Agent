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

> Fiches régénérées à partir de faits bruts (signature, retour, effet observable, contraintes), sans reprise de la rédaction du manuel. Méthode : voir `SOURCES.md`.

---

## AfterBirth
**Signature** : `Person AfterBirth()`  
- **Retour** : `Person` ; `?` si pas de Person liée
- **Paramètres** : 0
- **Effet** : navigation fœtus -> Person créée à la naissance (lien vers le fœtus)

---

## AntigenAntibody
**Signature** : `PersonAntigen AntigenAntibody(Mnemonic AntigenMnemonic)`  
- **Retour** : `PersonAntigen` ; `?` si antigène non enregistré
- **Paramètres** : 1 — `AntigenMnemonic` (Mnemonic)
- **Effet** : lecture de la ligne PersonAntigen pour un antigène (présence/absence + avis de typage)

---

## AntigenByNumber
**Signature** : `PersonAntigen AntigenByNumber(PositiveInteger Number)`  
- **Retour** : `PersonAntigen` ; `?` si rang hors plage
- **Paramètres** : 1 — `Number` (PositiveInteger)
- **Effet** : lecture de la n-ième ligne PersonAntigen ; ordre = numéro de séquence de la table Antigen

---

## AvailableBloodBagByNumber
**Signature** : `BloodBag AvailableBloodBagByNumber(Mnemonic ProductMnemonic, Logical Autologous, BloodBagStatus Status, PositiveInteger Number)`  
- **Retour** : `BloodBag` ; `?` si rang hors plage
- **Paramètres** : 4 — `ProductMnemonic` (Mnemonic), `Autologous` (Logical), `Status` (BloodBagStatus), `Number` (PositiveInteger)
- **Effet** : n-ième poche au statut Initial attribuée à la personne

---

## BloodForPersonAvailable
**Signature** : `Logical BloodForPersonAvailable(Mnemonic ProductMnemonic, Logical Autologous, Mnemonic DepartmentMnemonic, BloodBagStatus Status)`  
- **Retour** : `Logical`
- **Paramètres** : 4 — `ProductMnemonic` (Mnemonic), `Autologous` (Logical), `DepartmentMnemonic` (Mnemonic), `Status` (BloodBagStatus)
- **Effet** : YES si >= 1 poche au statut Initial pour la personne

---

## CalculateMedidocCaseNumber
**Signature** : `String CalculateMedidocCaseNumber()`  
- **Retour** : `String`
- **Paramètres** : 0
- **Effet** : calcul du numéro de dossier Medidoc de la personne
- **Portée** : Belgique (BE) uniquement

---

## GetAntibody
**Signature** : `Logical GetAntibody(String AntigenMnemonic)`  
- **Retour** : `Logical`
- **Paramètres** : 1 — `AntigenMnemonic` (String)
- **Effet** : test de présence d'un anticorps (mnémonique d'antigène)

---

## GetEncountersList
**Signature** : `String GetEncountersList()`  
- **Retour** : `String`
- **Paramètres** : 0
- **Effet** : liste (String) des visites ouvertes de la personne

---

## GetMedicalRecord
**Signature** : `PersonMedicalRecord GetMedicalRecord()`  
- **Retour** : `PersonMedicalRecord`
- **Paramètres** : 0
- **Effet** : accès à l'enregistrement PersonMedicalRecord

---

## GetTypingAdvice
**Signature** : `Logical GetTypingAdvice(String BloodBagInternalId, String AntigenMnemonic)`  
- **Retour** : `Logical`
- **Paramètres** : 2 — `BloodBagInternalId` (String), `AntigenMnemonic` (String)
- **Effet** : lecture de l'avis de typage pour une poche et un antigène

---

## HLAAntibody
**Signature** : `PersonHLAAntibody HLAAntibody(Mnemonic AntibodyMnemonic)`  
- **Retour** : `PersonHLAAntibody` ; `?` si anticorps absent
- **Paramètres** : 1 — `AntibodyMnemonic` (Mnemonic)
- **Effet** : ligne PersonHLAAntibody pour un anticorps donné

---

## HLAAntibodyByNumber
**Signature** : `PersonHLAAntibody HLAAntibodyByNumber(PositiveInteger Number)`  
- **Retour** : `PersonHLAAntibody` ; `?` si rang hors plage
- **Paramètres** : 1 — `Number` (PositiveInteger)
- **Effet** : n-ième ligne PersonHLAAntibody

---

## HLAAntigen
**Signature** : `PersonHLAAntigen HLAAntigen(Mnemonic AntigenMnemonic)`  
- **Retour** : `PersonHLAAntigen` ; `?` si antigène absent
- **Paramètres** : 1 — `AntigenMnemonic` (Mnemonic)
- **Effet** : ligne PersonHLAAntigen pour un antigène donné

---

## HLAAntigenByNumber
**Signature** : `PersonHLAAntigen HLAAntigenByNumber(PositiveInteger Number)`  
- **Retour** : `PersonHLAAntigen` ; `?` si rang hors plage
- **Paramètres** : 1 — `Number` (PositiveInteger)
- **Effet** : n-ième ligne PersonHLAAntigen

---

## OtherAntigens
**Signature** : `String OtherAntigens()`  
- **Retour** : `String`
- **Paramètres** : 0
- **Effet** : chaîne des antigènes hors Rhésus, format « MNEMO+ » ou « MNEMO- » séparés par espace

---

## RelationsOverview
**Signature** : `String RelationsOverview(Mnemonic TextMnemonic, String Type, Logical Recursive)`  
- **Retour** : `String`
- **Paramètres** : 3 — `TextMnemonic` (Mnemonic), `Type` (String), `Recursive` (Logical)
- **Effet** : texte généré : module de texte (table Person) répété pour chaque personne liée ; tri type puis nom ; option récursive

---

## RhesusPhenoType
**Signature** : `String RhesusPhenoType()`  
- **Retour** : `String`
- **Paramètres** : 0
- **Effet** : chaîne du phénotype Rhésus, format « MNEMO+ » ou « MNEMO- » séparés par espace

---

## SetAntibody
**Signature** : `Logical SetAntibody(String AntigenMnemonic, Logical Presence)`  
- **Retour** : `Logical`
- **Paramètres** : 2 — `AntigenMnemonic` (String), `Presence` (Logical)
- **Effet** : anticorps (mnémonique d'antigène) : Presence = YES -> noté présent, NO -> noté absent
- **Propriété** : Active

---

## SetHLAAntibodyPresence
**Signature** : `Logical SetHLAAntibodyPresence(Mnemonic AntibodyName, Date TheDate, Logical Presence)`  
- **Retour** : `Logical`
- **Paramètres** : 3 — `AntibodyName` (Mnemonic), `TheDate` (Date), `Presence` (Logical)
- **Effet** : enregistre présence/absence d'un anticorps HLA à une date
- **Propriété** : Active

---

## SetHLAAntibodyRValue
**Signature** : `Logical SetHLAAntibodyRValue(Mnemonic AntibodyName, Date TheDate, PositiveFractional RValue)`  
- **Retour** : `Logical`
- **Paramètres** : 3 — `AntibodyName` (Mnemonic), `TheDate` (Date), `RValue` (PositiveFractional)
- **Effet** : enregistre la valeur R d'un anticorps HLA à une date
- **Propriété** : Active

---

## SetHLAAntigenPresence
**Signature** : `Logical SetHLAAntigenPresence(Mnemonic AntigenName, Logical Presence)`  
- **Retour** : `Logical`
- **Paramètres** : 2 — `AntigenName` (Mnemonic), `Presence` (Logical)
- **Effet** : ligne HLA de la personne : Presence = YES présent, NO absent, ? suppression de la ligne
- **Propriété** : Active

---

## SetMedicalRecord
**Signature** : `Logical SetMedicalRecord(String FieldName, String FieldValue)`  
- **Retour** : `Logical`
- **Paramètres** : 2 — `FieldName` (String), `FieldValue` (String)
- **Effet** : écriture d'un champ (nom, valeur) du dossier médical de la personne
- **Propriété** : Active

---

## SetTypingAdvice
**Signature** : `Logical SetTypingAdvice(Mnemonic AntigenMnemonic, Logical Value)`  
- **Retour** : `Logical`
- **Paramètres** : 2 — `AntigenMnemonic` (Mnemonic), `Value` (Logical)
- **Effet** : écrit l'avis de typage (PersonAntigen) pour un antigène ; crée la ligne si absente
- **Propriété** : Active

---

## Stays
**Signature** : `String Stays()`  
- **Retour** : `String`
- **Paramètres** : 0
- **Effet** : liste (String) des séjours ouverts de la personne
