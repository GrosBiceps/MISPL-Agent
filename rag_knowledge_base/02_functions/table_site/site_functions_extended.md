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

## AllowedAbrechnungsGebietValues (ssit)
**Signature** : `String Allowed Abrechnungs Gebiet Values(String Scheinuntergruppe,String OKVKennung,String Quarter)`  
Cette fonction est réservée aux clients allemands.  

---

## AllowedKTABValues (ssit)
**Signature** : `String Allowed KTABValues(String OKVKennung,String Quarter)`  
Cette fonction est réservée aux clients allemands.  

---

## AllowedScheinuntergruppeValues (ssit)
**Signature** : `String Allowed Scheinuntergruppe Values(String OKVKennung,String Quarter)`  
Cette fonction est réservée aux clients allemands.  

---

## EncodeXDTPolicyName (ssit)
**Signature** : `String Encode XDTPolicy Name(String Gebuhrenordnung,String KTAB,String Abrechnungstyp)`  
Cette fonction est réservée aux clients allemands.  

---

## EuroToLocal (ssit)
**Signature** : `Fractional Euro To Local(Fractional Amount In Euro,Positive Integer Decimal Count)`  
Cette fonction convertit le montant donné (exprimé en euro) en le montant correspondant exprimé en monnaie locale.  

---

## ExonerationFraction (ssit)
**Signature** : `Fractional Exoneration Fraction(Logical ALD,Logical Baby,Logical CMU,Logical FSV,Logical Private Accident,Logical Work Accident,String Code ALD,String Code Situation,String Code Regime,String Code Acte,String Prescriptor Specialism,String Extra)`  
Cette fonction est réservée aux clients français et permet de calculer la partie à rembourser par la caisse primaire (France).  

---

## ExonerationJustification (ssit)
**Signature** : `Integer Exoneration Justification(Logical ALD,Logical Baby,Logical CMU,Logical FSV,Logical Private Accident,Logical Work Accident,String Code ALD,String Code Situation,String Code Regime,String Code Acte,String Prescriptor Specialism,String Extra)`  
Cette fonction est réservée aux clients français et permet de calculer le code 'justification d'exonération'.  

---

## ExonerationNature (ssit)
**Signature** : `Integer Exoneration Nature(Logical ALD,Logical Baby,Logical CMU,Logical FSV,Logical Private Accident,Logical Work Accident,String Code ALD,String Code Situation,String Code Regime,String Code Acte,String Prescriptor Specialism,String Extra)`  
Cette fonction est réservée aux clients français et permet de calculer la 'nature d'assurance'.  

---

## GetAbrechnungsArt (ssit)
**Signature** : `Positive Integer Get Abrechnungs Art(String OKVKennung,String Quarter,String Short VKNR,String KTAB)`  
Cette fonction est réservée aux clients allemands.  

---

## GetDepartment (ssit)
**Signature** : `Department Get Department(String Department Mnemonic)`  
Get the department record that corresponds with the given mnemonic.  

---

## GetDiagnosisCode (ssit)
**Signature** : `Diagnosis Code Get Diagnosis Code(String Diagnosis Code Code,Diagnosis Code System System,Mnemonic System Mnemonic)`  
Cette fonction permet de chercher le code diagnostic.  

---

## GetExecutingLab (ssit)
**Signature** : `String Get Executing Lab(Integer Nth Lab)`  
Cette fonction n'est disponible que dans un contexte donné: édition de documents de cotation.  

---

## GetFundId (ssit)
**Signature** : `Fund Get Fund Id(Mnemonic Fund Mnemonic)`  
Cette fonction permet de récupérer une référence à la caisse spécifiée.  

---

## GetHLAAntigen (ssit)
**Signature** : `HLAAntigen Get HLAAntigen(String Antigen Name)`  
This function returns a reference to the HLA antigen object that corresponds with the name given.  

---

## GetInvoiceId (ssit)
**Signature** : `Invoice Get Invoice Id(Firm Firm Id,String Doc No,Positive Integer Version No)`  
Cette fonction permet de récupérer une référence à la facture spécifiée.  

---

## GetInvoiceSummaryId (ssit)
**Signature** : `Invoice Summary Get Invoice Summary Id(Firm Firm Id,String Doc No)`  
Cette fonction récupère une référence au relevé spécifié.  

---

## GetLogEntry (gsit)
**Signature** : `lg_Entry Get Log Entry(String Table Name,Positive Integer Record Id,String Log Type Name,Logical Needs Checking,Log Severity Log Severity,Date Time Created After,Date Time Created Before,String Message Match String,Positive Integer Seq No)`  
This function accesses a log entry record based on the input parameters : if success then a reference to the record is returned, otherwise ?.  

---

## GetPolicyNameId (ssit)
**Signature** : `Policy Name Get Policy Name Id(String Policy Name Code,Fund Fund Id,Logical Can Use Default Policy Name)`  
Cette fonction permet de récupérer une référence au nom de police répondant aux critères spécifiés.  

---

## GetPrinterId (ssit)
**Signature** : `rp_Printer Get Printer Id(String Printer Name)`  
Cette fonction permet de récupérer une référence à l'imprimante spécifiée.  

---

## GetProvision (ssit)
**Signature** : `Provision Get Provision(Mnemonic Lab Mnemonic,Mnemonic Department Mnemonic,Mnemonic Executing Class Mnemonic,Date Time Time)`  
Permet l'accès aux dispositions à l'aide de MISPL.  

---

## GetStay (ssit)
**Signature** : `Stay Get Stay(String Stay Id)`  
Returns a Stay based on an ID.  

---

## GetVertragsarztId (ssit)
**Signature** : `Vertragsarztnummer Get Vertragsarzt Id(String Vertragsarztnummer,Date Validitydate,Integer Nth Record)`  
Cette fonction est réservée aux clients allemands.  

---

## Glims (ssit)
**Signature** : `Specific Site Glims()`  
Exemple: RETURN IfKnownString(Glims().  

---

## LocalToEuro (ssit)
**Signature** : `Fractional Local To Euro(Fractional Amount In Local Currency,Positive Integer Decimals)`  
Cette fonction permet de convertir le montant donné (exprimé en monnaie locale) en le montant correspondant exprimé en euro.  

---

## PaymentAgreements (ssit)
**Signature** : `String Payment Agreements(String Policy Name Code,Positive Integer Correspondent Id,Positive Integer Fund Id,Date Validity Date)`  
Cette fonction récupère une liste d'identifiants d'accord de paiement qui répondent aux critères spécifiés.  

---

## TariffingData (ssit)
**Signature** : `String Tariffing Data(String What To Retrieve)`  
Cette fonction peut récupérer des données générales de tarification: ces données ne sont disponibles que lors de la tarification.  

---

## ToEuro (ssit)
**Signature** : `Fractional To Euro(Fractional Amount,Positive Integer Decimal Count)`  
Si les montants stockés dans GLIMS ne sont pas encore exprimés en euro, cette fonction permet de convertir le montant en le montant correspondant exprimé en euro.  

---

## ToLocal (ssit)
**Signature** : `Fractional To Local(Fractional Amount,Positive Integer Decimal Count)`  
Si les montants stockés dans GLIMS sont exprimés en euro, cette fonction permet de convertir le montant en le montant correspondant exprimé en monnaie locale.  

---
