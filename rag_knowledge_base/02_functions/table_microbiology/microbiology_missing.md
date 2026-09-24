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

> Fiches régénérées à partir de faits bruts (signature, retour, effet observable, contraintes), sans reprise de la rédaction du manuel. Méthode : voir `SOURCES.md`.

---

## AntibioticResultIndexed (isol)
**Signature** : `AntibioticResult AntibioticResultIndexed(PositiveInteger Number)`  
- **Retour** : `AntibioticResult` ; `?` si rang hors plage
- **Paramètres** : 1 — `Number` (PositiveInteger)
- **Effet** : n-ième AntibioticResult de l'isolement

---

## ApproachActivity (actn)
**Signature** : `ApproachActivity ApproachActivity()`  
- **Retour** : `ApproachActivity` ; `?` si aucune
- **Paramètres** : 0
- **Effet** : ApproachActivity (génétique) liée à l'action

---

## GetSequence (isol)
**Signature** : `Integer GetSequence(Mnemonic SequenceTypeMnemonic)`  
- **Retour** : `Integer`
- **Paramètres** : 1 — `SequenceTypeMnemonic` (Mnemonic)
- **Effet** : numéro de séquence d'un type donné
- **Propriété** : Active

---

## GetStorageList (isol)
**Signature** : `String GetStorageList()`  
- **Retour** : `String`
- **Paramètres** : 0
- **Effet** : liste des stockages de l'isolement

---

## IsolationTestCount (mcra)
**Signature** : `PositiveInteger IsolationTestCount(String OrganismMnemonicList, String TestMnemonicList, Logical Aerobe, String OrganismBillingMarkList, Logical ReportableOnly, Logical PositiveOnly, Logical AnsweredOnly)`  
- **Retour** : `PositiveInteger`
- **Paramètres** : 7 — `OrganismMnemonicList` (String), `TestMnemonicList` (String), `Aerobe` (Logical), `OrganismBillingMarkList` (String), `ReportableOnly` (Logical), `PositiveOnly` (Logical), `AnsweredOnly` (Logical)
- **Effet** : nombre de tests d'isolement (filtres organismes, tests, aérobie, marques, rapportable, positif, répondu)

---

## SpecimenInput (actn)
**Signature** : `SpecimenInput SpecimenInput()`  
- **Retour** : `SpecimenInput`
- **Paramètres** : 0
- **Effet** : SpecimenInput de l'action
