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

> Fiches régénérées à partir de faits bruts (signature, retour, effet observable, contraintes), sans reprise de la rédaction du manuel. Méthode : voir `SOURCES.md`.

---

## Budget
**Signature** : `Budget Budget(Mnemonic BudgetClassMnemonic, InvoiceGroupingPeriod Period, Date ValidityDate)`  
- **Retour** : `Budget` ; `?` si aucun
- **Paramètres** : 3 — `BudgetClassMnemonic` (Mnemonic), `Period` (InvoiceGroupingPeriod), `ValidityDate` (Date)
- **Effet** : Budget du correspondant pour classe de budget, période de regroupement, date de validité

---

## Company
**Signature** : `Company Company()`  
- **Retour** : `Company` ; `?` si correspondant d'un autre type
- **Paramètres** : 0
- **Effet** : enregistrement Company lié

---

## CreateIdentification
**Signature** : `Logical CreateIdentification(Correspondent Source, String Code, Date StartDate, Date EndDate)`  
- **Retour** : `Logical`
- **Paramètres** : 4 — `Source` (Correspondent), `Code` (String), `StartDate` (Date), `EndDate` (Date)
- **Effet** : crée une identification (source, code, début, fin) sur ce correspondant

---

## HCProvider
**Signature** : `HCProvider HCProvider()`  
- **Retour** : `HCProvider` ; `?` si correspondant d'un autre type
- **Paramètres** : 0
- **Effet** : enregistrement HCProvider lié

---

## HealthOffice
**Signature** : `HealthOffice HealthOffice()`  
- **Retour** : `HealthOffice` ; `?` si correspondant d'un autre type
- **Paramètres** : 0
- **Effet** : enregistrement HealthOffice lié

---

## KnownIdentification
**Signature** : `Identification KnownIdentification(String ExternalId, Date ValidityDate)`  
- **Retour** : `Identification` ; `?` si aucune
- **Paramètres** : 2 — `ExternalId` (String), `ValidityDate` (Date)
- **Effet** : identification par identifiant externe et date de validité

---

## Organization
**Signature** : `Organization Organization()`  
- **Retour** : `Organization` ; `?` si correspondant d'un autre type
- **Paramètres** : 0
- **Effet** : enregistrement Organization lié

---

## PreviousFinancing
**Signature** : `String PreviousFinancing(Date ValidityDate)`  
- **Retour** : `String`
- **Paramètres** : 1 — `ValidityDate` (Date)
- **Effet** : identifiants des accords de paiement du dernier groupe de dossiers, liste

---

## Study
**Signature** : `Study Study()`  
- **Retour** : `Study` ; `?` si correspondant d'un autre type
- **Paramètres** : 0
- **Effet** : enregistrement Study lié

---

## TourMnemonicList
**Signature** : `String TourMnemonicList(String Pattern)`  
- **Retour** : `String`
- **Paramètres** : 1 — `Pattern` (String)
- **Effet** : mnémoniques des tournées du correspondant, CSV, tri par mnémonique ; filtre Pattern optionnel
