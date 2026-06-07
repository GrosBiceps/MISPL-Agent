---
id: "functions_object_missing"
type: "fonction_core"
domaine: "object_missing"
langage_proxy: "Progress ABL / OpenEdge"
context: ["action", "result"]
table_abbrev: "obj"
return_type: "String | Logical | Integer | Object"
priority: "medium"
keywords_fr: ["historique microbiologique", "attribut periode", "resultat objet", "donnees patient", "PIN patient", "lot objet", "animal", "graphe historique"]
anti_hallucination: []
tags: [Object, MicrobiologicHistory, AttributePeriod, GetResult, BuildHistoryGraph, PatientData, PersonData, PIN, Lot, GetLocusResult, GetVariantResult, GetPhoneLog, HasExternalInfo]
---

# Fonctions OBJ — complément exhaustif

## Animal
**Signature** : `Animal Animal()`  

---

## AttributePeriod
**Signature** : `Positive Integer Attribute Period(Mnemonic Attribute Mnemonic,Date Reference Date)`  
Returns the number of days the attribute is/was applicable for the specified object, at the specified reference date.  

---

## BloodSelectionByNumber
**Signature** : `Blood Selection Blood Selection By Number(Mnemonic Product Mnemonic,Blood Selection Status Minimal Status,Blood Selection Status Maximal Status,Positive Integer Number)`  

---

## BuildHistoryGraph
**Signature** : `String Build History Graph(String Tagged Parameter List)`  
Cette fonction génère un graphique historique de résultats précédents pour l'objet actuel au format XML.  

---

## CheckDiagnosisCodeCompatibility
**Signature** : `String Check Diagnosis Code Compatibility(Diagnosis Code Diagnosis Code,Date Reference Date,Logical Mustbe Billable)`  
Checks if the specified diagnosis code is compatible (german KBV attributes Sex, Age,.  

---

## FindMostRecentBilledBillingCode
**Signature** : `Billing Item Find Most Recent Billed Billing Code(String Billing Code,Date Start Date,Date End Date)`  
Cette méthode récupère l'enregistrement élément de cotation qui correspond à la date la plus récente à laquelle le code de cotation spécifié était facturé pour cet objet.  

---

## GetBloodBag
**Signature** : `Blood Bag Get Blood Bag(String Blood Product Mnemonic,Integer History Index,Date Time Minimal Backwards Time,Date Time Maximal Backwards Time)`  
L'historique de transfusions de sang consiste en informations sur les poches de sang auparavant administrées au patient.  

---

## GetCheckedOutBag
**Signature** : `Blood Bag Get Checked Out Bag(String Blood Product Mnemonic,Integer History Index,Date Time Minimal Backwards Time,Date Time Maximal Backwards Time)`  
Cette méthode permet de récupérer des poches de sang émises qui ne sont pas encore administrées.  

---

## GetLastBillingItemByReceiptDate
**Signature** : `Billing Item Get Last Billing Item By Receipt Date(String Billing Code,Date Start Date,Date End Date)`  
Cette méthode récupère l'enregistrement élément de cotation qui correspond à la date (date de tarification = date externe facture) la plus récente à laquelle le code cotation spécifié était facturé po.  

---

## GetLocusResult
**Signature** : `Locus Result Get Locus Result(String Locus Name,Locus Result Status Minimal Status,Integer Minimal Severity,Integer Index)`  
Returns a reference to a specific locus result of the object.  

---

## GetPhoneLog
**Signature** : `Phone Log Get Phone Log(Phone Log Previous,Logical Phoned)`  
La fonction MISPL Object.  

---

## GetVariantResult
**Signature** : `Variant Result Get Variant Result(String Variant Name,Variant Result Status Minimal Status,Integer Minimal Severity,Integer Minimal Classification,Variant Retest Status Retest Status,Integer Index)`  
Returns a reference to a specific variant result of the object.  

---

## HasExternalInfo
**Signature** : `Logical Has External Info()`  
Récupère si des infos externes sont disponibles dans le système info externe indiqué.  

---

## Lot
**Signature** : `Lot Lot()`  

---

## NumberOfBilledBillingCodes
**Signature** : `Positive Integer Number Of Billed Billing Codes(String Billing Code,Date Start Date,Date End Date)`  
Cette méthode récupère le nombre de fois qu'un code cotation était facturé pour un objet, en fonction du code cotation mentionné et lors de la période donnée.  

---

## QCLot
**Signature** : `QCLot QCLot()`  
La fonction MISPL Object.  

---
