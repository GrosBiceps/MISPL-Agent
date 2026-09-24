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

> Fiches régénérées à partir de faits bruts (signature, retour, effet observable, contraintes), sans reprise de la rédaction du manuel. Méthode : voir `SOURCES.md`.

---

## Animal
**Signature** : `Animal Animal()`  
- **Retour** : `Animal` ; `?` si objet non animal
- **Paramètres** : 0
- **Effet** : accès à l'enregistrement Animal de l'objet

---

## AttributePeriod
**Signature** : `PositiveInteger AttributePeriod(Mnemonic AttributeMnemonic, Date ReferenceDate)`  
- **Retour** : `PositiveInteger` ; `?` si attribut absent
- **Paramètres** : 2 — `AttributeMnemonic` (Mnemonic), `ReferenceDate` (Date)
- **Effet** : nombre de jours d'application d'un attribut à ReferenceDate ; date ? = aujourd'hui

---

## BloodSelectionByNumber
**Signature** : `BloodSelection BloodSelectionByNumber(Mnemonic ProductMnemonic, BloodSelectionStatus MinimalStatus, BloodSelectionStatus MaximalStatus, PositiveInteger Number)`  
- **Retour** : `BloodSelection` ; `?` si rang hors plage
- **Paramètres** : 4 — `ProductMnemonic` (Mnemonic), `MinimalStatus` (BloodSelectionStatus), `MaximalStatus` (BloodSelectionStatus), `Number` (PositiveInteger)
- **Effet** : n-ième BloodSelection filtrée par produit et plage de statuts

---

## BuildHistoryGraph
**Signature** : `String BuildHistoryGraph(String TaggedParameterList)`  
- **Retour** : `String`
- **Paramètres** : 1 — `TaggedParameterList` (String)
- **Effet** : XML de graphique d'historique des résultats (usage : comptes rendus Word)

---

## CheckDiagnosisCodeCompatibility
**Signature** : `String CheckDiagnosisCodeCompatibility(DiagnosisCode DiagnosisCode, Date ReferenceDate, Logical MustbeBillable)`  
- **Retour** : `String`
- **Paramètres** : 3 — `DiagnosisCode` (DiagnosisCode), `ReferenceDate` (Date), `MustbeBillable` (Logical)
- **Effet** : contrôle code diagnostic / attributs patient (sexe, âge) ; retour "" si compatible, sinon message
- **Portée** : Allemagne (DE) uniquement

---

## FindMostRecentBilledBillingCode
**Signature** : `BillingItem FindMostRecentBilledBillingCode(String BillingCode, Date StartDate, Date EndDate)`  
- **Retour** : `BillingItem` ; `?` si aucune facturation
- **Paramètres** : 3 — `BillingCode` (String), `StartDate` (Date), `EndDate` (Date)
- **Effet** : BillingItem de la dernière facturation du code dans [StartDate ; EndDate]

---

## GetBloodBag
**Signature** : `BloodBag GetBloodBag(String BloodProductMnemonic, Integer HistoryIndex, DateTime MinimalBackwardsTime, DateTime MaximalBackwardsTime)`  
- **Retour** : `BloodBag` ; `?` si aucune poche
- **Paramètres** : 4 — `BloodProductMnemonic` (String), `HistoryIndex` (Integer), `MinimalBackwardsTime` (DateTime), `MaximalBackwardsTime` (DateTime)
- **Effet** : poche transfusée n° HistoryIndex de l'historique, filtrée par produit et fenêtre temporelle

---

## GetCheckedOutBag
**Signature** : `BloodBag GetCheckedOutBag(String BloodProductMnemonic, Integer HistoryIndex, DateTime MinimalBackwardsTime, DateTime MaximalBackwardsTime)`  
- **Retour** : `BloodBag` ; `?` si aucune poche
- **Paramètres** : 4 — `BloodProductMnemonic` (String), `HistoryIndex` (Integer), `MinimalBackwardsTime` (DateTime), `MaximalBackwardsTime` (DateTime)
- **Effet** : poche délivrée non transfusée n° HistoryIndex, filtrée par produit et fenêtre temporelle

---

## GetLastBillingItemByReceiptDate
**Signature** : `BillingItem GetLastBillingItemByReceiptDate(String BillingCode, Date StartDate, Date EndDate)`  
- **Retour** : `BillingItem` ; `?` si aucune facturation
- **Paramètres** : 3 — `BillingCode` (String), `StartDate` (Date), `EndDate` (Date)
- **Effet** : BillingItem le plus récent pour le code, critère = date externe de facture

---

## GetLocusResult
**Signature** : `LocusResult GetLocusResult(String LocusName, LocusResultStatus MinimalStatus, Integer MinimalSeverity, Integer Index)`  
- **Retour** : `LocusResult` ; `?` si aucun
- **Paramètres** : 4 — `LocusName` (String), `MinimalStatus` (LocusResultStatus), `MinimalSeverity` (Integer), `Index` (Integer)
- **Effet** : LocusResult de l'objet selon locus, statut minimal, sévérité minimale, rang

---

## GetPhoneLog
**Signature** : `PhoneLog GetPhoneLog(PhoneLog Previous, Logical Phoned)`  
- **Retour** : `PhoneLog` ; `?` si fin de liste
- **Paramètres** : 2 — `Previous` (PhoneLog), `Phoned` (Logical)
- **Effet** : itération sur les PhoneLog de l'objet ; filtre Phoned

---

## GetVariantResult
**Signature** : `VariantResult GetVariantResult(String VariantName, VariantResultStatus MinimalStatus, Integer MinimalSeverity, Integer MinimalClassification, VariantRetestStatus RetestStatus, Integer Index)`  
- **Retour** : `VariantResult` ; `?` si aucun
- **Paramètres** : 6 — `VariantName` (String), `MinimalStatus` (VariantResultStatus), `MinimalSeverity` (Integer), `MinimalClassification` (Integer), `RetestStatus` (VariantRetestStatus), `Index` (Integer)
- **Effet** : VariantResult de l'objet selon variant, statut, sévérité, classification, statut de retest, rang

---

## HasExternalInfo
**Signature** : `Logical HasExternalInfo()`  
- **Retour** : `Logical`
- **Paramètres** : 0
- **Effet** : YES si le système d'informations externes signale des données pour l'objet

---

## Lot
**Signature** : `Lot Lot()`  
- **Retour** : `Lot` ; `?` si objet non lot
- **Paramètres** : 0
- **Effet** : accès à l'enregistrement Lot de l'objet

---

## NumberOfBilledBillingCodes
**Signature** : `PositiveInteger NumberOfBilledBillingCodes(String BillingCode, Date StartDate, Date EndDate)`  
- **Retour** : `PositiveInteger`
- **Paramètres** : 3 — `BillingCode` (String), `StartDate` (Date), `EndDate` (Date)
- **Effet** : nombre de facturations d'un code dans [StartDate ; EndDate]

---

## QCLot
**Signature** : `QCLot QCLot()`  
- **Retour** : `QCLot` ; `?` si objet non lot CQ
- **Paramètres** : 0
- **Effet** : accès à l'enregistrement QCLot (objet de type lot CQ)
