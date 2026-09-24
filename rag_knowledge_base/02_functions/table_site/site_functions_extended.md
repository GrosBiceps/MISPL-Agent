---
id: "functions_site_extended"
type: "fonction_core"
domaine: "site_extended"
langage_proxy: "Progress ABL / OpenEdge"
context: ["all"]
table_abbrev: "ssit"
return_type: "String | Logical | Integer | Object"
priority: "low"
keywords_fr: ["recuperer encounter par ID", "recuperer sejour", "provision laboratoire", "GetLogEntry", "code diagnostic", "departement par mnemonic"]
anti_hallucination: []
tags: [SpecificSite, ssit, gp_Site, gsit, GetStay, GetEncounter, GetProvision, GetLogEntry, GetDiagnosisCode, GetDepartment]
---


# Fonctions SSIT + GSIT — complément exhaustif

> Fiches régénérées à partir de faits bruts (signature, retour, effet observable, contraintes), sans reprise de la rédaction du manuel. Méthode : voir `SOURCES.md`.

---

## AllowedAbrechnungsGebietValues (ssit)
**Signature** : `String AllowedAbrechnungsGebietValues(String Scheinuntergruppe, String OKVKennung, String Quarter)`  
- **Retour** : `String`
- **Paramètres** : 3 — `Scheinuntergruppe` (String), `OKVKennung` (String), `Quarter` (String)
- **Effet** : valeurs autorisées d'AbrechnungsGebiet (KV, Scheinuntergruppe, trimestre)
- **Portée** : Allemagne (DE) uniquement

---

## AllowedKTABValues (ssit)
**Signature** : `String AllowedKTABValues(String OKVKennung, String Quarter)`  
- **Retour** : `String`
- **Paramètres** : 2 — `OKVKennung` (String), `Quarter` (String)
- **Effet** : valeurs KTAB autorisées (KV, trimestre)
- **Portée** : Allemagne (DE) uniquement

---

## AllowedScheinuntergruppeValues (ssit)
**Signature** : `String AllowedScheinuntergruppeValues(String OKVKennung, String Quarter)`  
- **Retour** : `String`
- **Paramètres** : 2 — `OKVKennung` (String), `Quarter` (String)
- **Effet** : valeurs de Scheinuntergruppe autorisées (KV, trimestre)
- **Portée** : Allemagne (DE) uniquement

---

## EncodeXDTPolicyName (ssit)
**Signature** : `String EncodeXDTPolicyName(String Gebuhrenordnung, String KTAB, String Abrechnungstyp)`  
- **Retour** : `String`
- **Paramètres** : 3 — `Gebuhrenordnung` (String), `KTAB` (String), `Abrechnungstyp` (String)
- **Effet** : encodage d'un nom de police xDT
- **Portée** : Allemagne (DE) uniquement

---

## EuroToLocal (ssit)
**Signature** : `Fractional EuroToLocal(Fractional AmountInEuro, PositiveInteger DecimalCount)`  
- **Retour** : `Fractional`
- **Paramètres** : 2 — `AmountInEuro` (Fractional), `DecimalCount` (PositiveInteger)
- **Effet** : conversion EUR -> devise locale, arrondi à DecimalCount
- **Contrainte** : obsolète : utiliser ToLocal

---

## ExonerationFraction (ssit)
**Signature** : `Fractional ExonerationFraction(Logical ALD, Logical Baby, Logical CMU, Logical FSV, Logical PrivateAccident, Logical WorkAccident, String CodeALD, String CodeSituation, String CodeRegime, String CodeActe, String PrescriptorSpecialism, String Extra)`  
- **Retour** : `Fractional`
- **Paramètres** : 12 — `ALD` (Logical), `Baby` (Logical), `CMU` (Logical), `FSV` (Logical), `PrivateAccident` (Logical), `WorkAccident` (Logical), `CodeALD` (String), `CodeSituation` (String), `CodeRegime` (String), `CodeActe` (String), `PrescriptorSpecialism` (String), `Extra` (String)
- **Effet** : part remboursée par la caisse primaire (critères d'exonération)
- **Portée** : France (FR) uniquement

---

## ExonerationJustification (ssit)
**Signature** : `Integer ExonerationJustification(Logical ALD, Logical Baby, Logical CMU, Logical FSV, Logical PrivateAccident, Logical WorkAccident, String CodeALD, String CodeSituation, String CodeRegime, String CodeActe, String PrescriptorSpecialism, String Extra)`  
- **Retour** : `Integer`
- **Paramètres** : 12 — `ALD` (Logical), `Baby` (Logical), `CMU` (Logical), `FSV` (Logical), `PrivateAccident` (Logical), `WorkAccident` (Logical), `CodeALD` (String), `CodeSituation` (String), `CodeRegime` (String), `CodeActe` (String), `PrescriptorSpecialism` (String), `Extra` (String)
- **Effet** : code « justification d'exonération »
- **Portée** : France (FR) uniquement

---

## ExonerationNature (ssit)
**Signature** : `Integer ExonerationNature(Logical ALD, Logical Baby, Logical CMU, Logical FSV, Logical PrivateAccident, Logical WorkAccident, String CodeALD, String CodeSituation, String CodeRegime, String CodeActe, String PrescriptorSpecialism, String Extra)`  
- **Retour** : `Integer`
- **Paramètres** : 12 — `ALD` (Logical), `Baby` (Logical), `CMU` (Logical), `FSV` (Logical), `PrivateAccident` (Logical), `WorkAccident` (Logical), `CodeALD` (String), `CodeSituation` (String), `CodeRegime` (String), `CodeActe` (String), `PrescriptorSpecialism` (String), `Extra` (String)
- **Effet** : code « nature d'assurance »
- **Portée** : France (FR) uniquement

---

## GetAbrechnungsArt (ssit)
**Signature** : `PositiveInteger GetAbrechnungsArt(String OKVKennung, String Quarter, String ShortVKNR, String KTAB)`  
- **Retour** : `PositiveInteger`
- **Paramètres** : 4 — `OKVKennung` (String), `Quarter` (String), `ShortVKNR` (String), `KTAB` (String)
- **Effet** : AbrechnungsArt (KV, trimestre, VKNR court, KTAB)
- **Portée** : Allemagne (DE) uniquement

---

## GetDepartment (ssit)
**Signature** : `Department GetDepartment(String DepartmentMnemonic)`  
- **Retour** : `Department` ; `?` si non trouvé
- **Paramètres** : 1 — `DepartmentMnemonic` (String)
- **Effet** : Department par mnémonique

---

## GetDiagnosisCode (ssit)
**Signature** : `DiagnosisCode GetDiagnosisCode(String DiagnosisCodeCode, DiagnosisCodeSystem System, Mnemonic SystemMnemonic)`  
- **Retour** : `DiagnosisCode` ; `?` si non trouvé
- **Paramètres** : 3 — `DiagnosisCodeCode` (String), `System` (DiagnosisCodeSystem), `SystemMnemonic` (Mnemonic)
- **Effet** : DiagnosisCode par code, système, mnémonique de système

---

## GetExecutingLab (ssit)
**Signature** : `String GetExecutingLab(Integer NthLab)`  
- **Retour** : `String`
- **Paramètres** : 1 — `NthLab` (Integer)
- **Effet** : identification du n-ième laboratoire exécutant
- **Contrainte** : uniquement en édition de documents de cotation

---

## GetFundId (ssit)
**Signature** : `Fund GetFundId(Mnemonic FundMnemonic)`  
- **Retour** : `Fund` ; `?` si non trouvé
- **Paramètres** : 1 — `FundMnemonic` (Mnemonic)
- **Effet** : Fund par mnémonique

---

## GetHLAAntigen (ssit)
**Signature** : `HLAAntigen GetHLAAntigen(String AntigenName)`  
- **Retour** : `HLAAntigen` ; `?` si non trouvé
- **Paramètres** : 1 — `AntigenName` (String)
- **Effet** : HLAAntigen par nom

---

## GetInvoiceId (ssit)
**Signature** : `Invoice GetInvoiceId(Firm FirmId, String DocNo, PositiveInteger VersionNo)`  
- **Retour** : `Invoice` ; `?` si aucune ou plusieurs
- **Paramètres** : 3 — `FirmId` (Firm), `DocNo` (String), `VersionNo` (PositiveInteger)
- **Effet** : Invoice par firme, n° de document, version

---

## GetInvoiceSummaryId (ssit)
**Signature** : `InvoiceSummary GetInvoiceSummaryId(Firm FirmId, String DocNo)`  
- **Retour** : `InvoiceSummary` ; `?` si non trouvé
- **Paramètres** : 2 — `FirmId` (Firm), `DocNo` (String)
- **Effet** : InvoiceSummary par firme et n° de document

---

## GetLogEntry (gsit)
**Signature** : `lg_Entry GetLogEntry(String TableName, PositiveInteger RecordId, String LogTypeName, Logical NeedsChecking, LogSeverity LogSeverity, DateTime CreatedAfter, DateTime CreatedBefore, String MessageMatchString, PositiveInteger SeqNo)`  
- **Retour** : `lg_Entry` ; `?` si non trouvée
- **Paramètres** : 9 — `TableName` (String), `RecordId` (PositiveInteger), `LogTypeName` (String), `NeedsChecking` (Logical), `LogSeverity` (LogSeverity), `CreatedAfter` (DateTime), `CreatedBefore` (DateTime), `MessageMatchString` (String), `SeqNo` (PositiveInteger)
- **Effet** : entrée de journal par critères (table, id, type, contrôle, sévérité, fenêtre de création, motif de message, rang)

---

## GetPolicyNameId (ssit)
**Signature** : `PolicyName GetPolicyNameId(String PolicyNameCode, Fund FundId, Logical CanUseDefaultPolicyName)`  
- **Retour** : `PolicyName` ; `?` si non trouvé
- **Paramètres** : 3 — `PolicyNameCode` (String), `FundId` (Fund), `CanUseDefaultPolicyName` (Logical)
- **Effet** : PolicyName par code et caisse ; option : repli sur le nom de police par défaut

---

## GetPrinterId (ssit)
**Signature** : `rp_Printer GetPrinterId(String PrinterName)`  
- **Retour** : `rp_Printer` ; `?` si non trouvé
- **Paramètres** : 1 — `PrinterName` (String)
- **Effet** : rp_Printer par nom

---

## GetProvision (ssit)
**Signature** : `Provision GetProvision(Mnemonic LabMnemonic, Mnemonic DepartmentMnemonic, Mnemonic ExecutingClassMnemonic, DateTime Time)`  
- **Retour** : `Provision` ; `?` si aucune
- **Paramètres** : 4 — `LabMnemonic` (Mnemonic), `DepartmentMnemonic` (Mnemonic), `ExecutingClassMnemonic` (Mnemonic), `Time` (DateTime)
- **Effet** : Provision (labo, discipline, classe d'exécution, instant)

---

## GetStay (ssit)
**Signature** : `Stay GetStay(String StayId)`  
- **Retour** : `Stay` ; `?` si non trouvé
- **Paramètres** : 1 — `StayId` (String)
- **Effet** : Stay par identifiant

---

## GetVertragsarztId (ssit)
**Signature** : `Vertragsarztnummer GetVertragsarztId(String Vertragsarztnummer, Date Validitydate, Integer NthRecord)`  
- **Retour** : `Vertragsarztnummer`
- **Paramètres** : 3 — `Vertragsarztnummer` (String), `Validitydate` (Date), `NthRecord` (Integer)
- **Effet** : enregistrement Vertragsarztnummer (numéro, date, rang)
- **Portée** : Allemagne (DE) uniquement

---

## Glims (ssit)
**Signature** : `SpecificSite Glims()`  
- **Retour** : `SpecificSite`
- **Paramètres** : 0
- **Effet** : accès à l'enregistrement SpecificSite du site

---

## LocalToEuro (ssit)
**Signature** : `Fractional LocalToEuro(Fractional AmountInLocalCurrency, PositiveInteger Decimals)`  
- **Retour** : `Fractional`
- **Paramètres** : 2 — `AmountInLocalCurrency` (Fractional), `Decimals` (PositiveInteger)
- **Effet** : conversion devise locale -> EUR, arrondi à Decimals
- **Contrainte** : obsolète : utiliser ToEuro

---

## PaymentAgreements (ssit)
**Signature** : `String PaymentAgreements(String PolicyNameCode, PositiveInteger CorrespondentId, PositiveInteger FundId, Date ValidityDate)`  
- **Retour** : `String`
- **Paramètres** : 4 — `PolicyNameCode` (String), `CorrespondentId` (PositiveInteger), `FundId` (PositiveInteger), `ValidityDate` (Date)
- **Effet** : identifiants d'accords de paiement (code de police, correspondant, caisse, date), liste

---

## TariffingData (ssit)
**Signature** : `String TariffingData(String WhatToRetrieve)`  
- **Retour** : `String`
- **Paramètres** : 1 — `WhatToRetrieve` (String)
- **Effet** : donnée générale de tarification demandée
- **Contrainte** : uniquement pendant la tarification

---

## ToEuro (ssit)
**Signature** : `Fractional ToEuro(Fractional Amount, PositiveInteger DecimalCount)`  
- **Retour** : `Fractional`
- **Paramètres** : 2 — `Amount` (Fractional), `DecimalCount` (PositiveInteger)
- **Effet** : conversion vers EUR, arrondi à DecimalCount ; cas : stockage en devise locale

---

## ToLocal (ssit)
**Signature** : `Fractional ToLocal(Fractional Amount, PositiveInteger DecimalCount)`  
- **Retour** : `Fractional`
- **Paramètres** : 2 — `Amount` (Fractional), `DecimalCount` (PositiveInteger)
- **Effet** : conversion vers la devise locale, arrondi à DecimalCount ; cas : stockage en EUR
