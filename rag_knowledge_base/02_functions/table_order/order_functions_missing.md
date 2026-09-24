---
id: "functions_order_missing"
type: "fonction_core"
domaine: "order_missing"
langage_proxy: "Progress ABL / OpenEdge"
context: ["action", "result", "order"]
table_abbrev: "ord"
return_type: "String | Logical | Integer | Object"
priority: "medium"
keywords_fr: ["cotation dossier", "recalculer prelevement", "todo dossier", "log telephonique", "items facturation", "accord paiement objet", "consultation", "image dossier"]
anti_hallucination: []
tags: [Order, TariffResult, ObjectPaymentAgreement, GetPhoneLog, InvoiceItemsData, RecalculateSpecimen, BudgetInvoice, Consult, SetImage, SetStudyEpisode, CreateReferral]
---


# Fonctions ORD — complément exhaustif

> Fiches régénérées à partir de faits bruts (signature, retour, effet observable, contraintes), sans reprise de la rédaction du manuel. Méthode : voir `SOURCES.md`.

---

## BudgetInvoice
**Signature** : `BudgetInvoice BudgetInvoice(Mnemonic BudgetClassMnemonic, ReimburserType OwnerType)`  
- **Retour** : `BudgetInvoice` ; `?` si aucune facture
- **Paramètres** : 2 — `BudgetClassMnemonic` (Mnemonic), `OwnerType` (ReimburserType)
- **Effet** : facture budgétaire du dossier pour une classe de budget et un type de payeur

---

## BudgetItemsOfParty
**Signature** : `String BudgetItemsOfParty(String BudgetClassList, ReimburserType OwnerType, Logical Separated, String InformationType)`  
- **Retour** : `String`
- **Paramètres** : 4 — `BudgetClassList` (String), `OwnerType` (ReimburserType), `Separated` (Logical), `InformationType` (String)
- **Effet** : données budgétaires du dossier pour un payeur ; valeur simple ou liste de tags

---

## CheckFSE
**Signature** : `String CheckFSE()`  
- **Retour** : `String`
- **Paramètres** : 0
- **Effet** : contrôle de complétude du dossier pour la FSE ; retour = liste de tags (lecture : ExtractTag)
- **Portée** : France (FR) uniquement

---

## CheckKVDT
**Signature** : `String CheckKVDT(Date CheckDate, String OKVKennung, XDTCharacterSet CharacterSet)`  
- **Retour** : `String`
- **Paramètres** : 3 — `CheckDate` (Date), `OKVKennung` (String), `CharacterSet` (XDTCharacterSet)
- **Effet** : contrôle KVDT du dossier à une date
- **Portée** : Allemagne (DE) uniquement

---

## Consult
**Signature** : `Consult Consult()`  
- **Retour** : `Consult` ; `?` si dossier non « consult »
- **Paramètres** : 0
- **Effet** : enregistrement Consult du dossier

---

## CreateReferral
**Signature** : `Void CreateReferral(String TaggedValueList)`  
- **Retour** : aucun (`Void`)
- **Paramètres** : 1 — `TaggedValueList` (String)
- **Effet** : création d'une demande d'adressage à partir d'une liste de valeurs taguées
- **Propriété** : Active

---

## GetClinicalConsultation
**Signature** : `ClinConsultation GetClinicalConsultation()`  
- **Retour** : `ClinConsultation` ; `?` si aucune
- **Paramètres** : 0
- **Effet** : ClinConsultation liée au dossier

---

## GetOrderTodoItem
**Signature** : `OrderTodoItem GetOrderTodoItem(Integer OrderTodoItemId)`  
- **Retour** : `OrderTodoItem` ; `?` si id inconnu
- **Paramètres** : 1 — `OrderTodoItemId` (Integer)
- **Effet** : tâche du dossier par identifiant

---

## GetOrderTodoItems
**Signature** : `String GetOrderTodoItems(String OrderTodoListMnemonic, Logical OrderTodoItemStatus)`  
- **Retour** : `String`
- **Paramètres** : 2 — `OrderTodoListMnemonic` (String), `OrderTodoItemStatus` (Logical)
- **Effet** : liste des tâches liées, filtre par liste ou par statut

---

## GetPhoneLog
**Signature** : `PhoneLog GetPhoneLog(PhoneLog Previous, Logical Phoned)`  
- **Retour** : `PhoneLog` ; `?` si fin de liste
- **Paramètres** : 2 — `Previous` (PhoneLog), `Phoned` (Logical)
- **Effet** : itération sur les PhoneLog du dossier ; filtre Phoned

---

## InvoiceItemsData
**Signature** : `String InvoiceItemsData(String PayerTypeList, String PriceCodeList, String ReimbursementClassList, String Value, String SeparateBy)`  
- **Retour** : `String`
- **Paramètres** : 5 — `PayerTypeList` (String), `PriceCodeList` (String), `ReimbursementClassList` (String), `Value` (String), `SeparateBy` (String)
- **Effet** : données des lignes de facture non rejetées, filtres payeur / code prix / classe de remboursement

---

## ObjectPaymentAgreement
**Signature** : `PaymentAgreement ObjectPaymentAgreement()`  
- **Retour** : `PaymentAgreement` ; `?` si aucun
- **Paramètres** : 0
- **Effet** : accord de paiement principal de la tarification

---

## RecalculateSpecimen
**Signature** : `Void RecalculateSpecimen()`  
- **Retour** : aucun (`Void`)
- **Paramètres** : 0
- **Effet** : recalcul de l'identifiant interne de tous les échantillons (discontinués compris)
- **Portée** : réservé éditeur

---

## SetImage
**Signature** : `Logical SetImage(String FileName)`  
- **Retour** : `Logical`
- **Paramètres** : 1 — `FileName` (String)
- **Effet** : écriture du champ Order.Image (référence document externe, p. ex. URL)
- **Propriété** : Active

---

## SetStudyEpisode
**Signature** : `Logical SetStudyEpisode(String Episode)`  
- **Retour** : `Logical`
- **Paramètres** : 1 — `Episode` (String)
- **Effet** : écriture du champ Episode du dossier
- **Propriété** : Active

---

## TariffResult
**Signature** : `Result TariffResult(String BillingCode, String PropertyMnemonic)`  
- **Retour** : `Result` ; `?` si aucun
- **Paramètres** : 2 — `BillingCode` (String), `PropertyMnemonic` (String)
- **Effet** : Result tarifé (code de facturation, analyse)
- **Contrainte** : uniquement pendant la tarification
