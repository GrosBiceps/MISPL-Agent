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

## BudgetInvoice
**Signature** : `Budget Invoice Budget Invoice(Mnemonic Budget Class Mnemonic,Reimburser Type Owner Type)`  
Récupérer la facture budgétaire spécifiée (si possible).  

---

## BudgetItemsOfParty
**Signature** : `String Budget Items Of Party(String Budget Class List,Reimburser Type Owner Type,Logical Separated,String Information Type)`  
Récupère de l'information budgétaire pour le dossier et l'organisme de remboursement spécifié.  

---

## CheckFSE
**Signature** : `String Check FSE()`  
Cette fonction MISPL vérifie l'état complet du dossier par rapport à la Feuille de Soins Electronique (FSE).  

---

## CheckKVDT
**Signature** : `String Check KVDT(Date Check Date,String OKVKennung,XDTCharacter Set Character Set)`  
Uniquement utilisé en Allemagne.  

---

## Consult
**Signature** : `Consult Consult()`  
Get the consult record for the current order, if it is a consult order.  

---

## CreateReferral
**Signature** : `Active Void Create Referral(String Tagged Value List)`  

---

## GetClinicalConsultation
**Signature** : `Clin Consultation Get Clinical Consultation()`  
Retrieve the Clinical Consultation linked to this Order.  

---

## GetOrderTodoItem
**Signature** : `Order Todo Item Get Order Todo Item(Integer Order Todo Item Id)`  
This function allows to retrieve a specific order to-do item of an order.  

---

## GetOrderTodoItems
**Signature** : `String Get Order Todo Items(String Order Todo List Mnemonic,Logical Order Todo Item Status)`  
Returns all linked order to-do items for a specific list or with a specific status.  

---

## GetPhoneLog
**Signature** : `Phone Log Get Phone Log(Phone Log Previous,Logical Phoned)`  

---

## InvoiceItemsData
**Signature** : `String Invoice Items Data(String Payer Type List,String Price Code List,String Reimbursement Class List,String Value,String Separate By)`  
Cette fonction récupère des données des éléments non rejetés des factures du dossier.  

---

## ObjectPaymentAgreement
**Signature** : `Payment Agreement Object Payment Agreement()`  
Récupère une référence à l'accord de paiement primaire utilisé pour tarifer le dossier.  

---

## RecalculateSpecimen
**Signature** : `Void Recalculate Specimen()`  
This MISPL allows to trigger recalculation of the internal id of all (including discontinued) specimen.  

---

## SetImage
**Signature** : `Active Logical Set Image(String File Name)`  
Renseigne le champ 'Order.  

---

## SetStudyEpisode
**Signature** : `Active Logical Set Study Episode(String Episode)`  
Change la valeur du champ 'Episode' au niveau Dossier en la valeur spécifiée comme paramètre.  

---

## TariffResult
**Signature** : `Result Tariff Result(String Billing Code,String Property Mnemonic)`  
Récupère une référence à un résultat tarifé du dossier.  

---
