---
id: "functions_table_microbiology"
type: "fonction_core"
domaine: "table_microbiology"
langage_proxy: "Progress ABL / OpenEdge"
context: ["action", "result"]
table_abbrev: ["mcra", "isol", "carr", "abrs"]
return_type: "String | Logical | Integer | Isolation | AntibioticResult"
priority: "medium"
keywords_fr: ["microbiologie", "antibiogramme", "isolement", "bactérie", "porteur", "milieu de culture", "conclusion microbiologie", "RIS résistance", "CMI", "résultat antibiogramme", "organisme", "statut microbiologie"]
anti_hallucination: []
tags: [MicrobiologyAction, mcra, Isolation, isol, Carrier, carr, AntibioticResult, abrs, AddIsolation, SetOrganism, SetRIS, ReplaceRIS, SetConclusion, AntibioticCount, IsolationCount, CarrierList, TextualSummary]
---

# Fonctions des tables Microbiologie

Tables GLIMS : `mcra` (MicrobiologyAction), `isol` (Isolation), `carr` (Carrier), `abrs` (AntibioticResult).

---

## MicrobiologyAction (mcra)

### AddIsolation
**Signature** : `Logical AddIsolation(Mnemonic OrganismMnemonic)`  
Ajoute un isolement (organisme identifié) à l'action microbiologique.

### AddCarriers
**Signature** : `Logical AddCarriers(String MnemonicList, Logical Print, Logical MarkAsGrafted, Logical DoubleAllowed, String Comment)`  
Ajoute des milieux de culture.

### IsolationCount
**Signature** : `PositiveInteger IsolationCount(String OrganismMnemonicList, Logical Aerobe, String OrganismBillingMarkList, Logical Reportable, String AppraisalList, Logical Anti...)`  
Compte les isolements selon des critères de filtrage.

### AntibioticCount / AntibioticResultCount
Comptent les antibiotiques testés / les résultats d'antibiogramme.

### CarrierCount / CarrierList
```
PositiveInteger CarrierCount(String MediumMnemonicList, String MediumTestMnemonicList)
String CarrierList(String Format)
```
Comptent les porteurs / retournent la liste formatée.

### SetConclusion
**Signature** : `Logical SetConclusion(String NewConclusion, Logical AppendConclusion)`  
Définit/ajoute la conclusion microbiologique.

```mispl
/* Ajouter une conclusion au rapport microbiologique */
.MicrobiologyAction().SetConclusion("Contamination probable — à répéter", NO);
```

### SetStatus
**Signature** : `Logical SetStatus(String StatusName, String ExtraInfo)`  
Change le statut de l'action microbiologique.

### SetEndOfIncubationTime
**Signature** : `Logical SetEndOfIncubationTime(DateTime EndOfIncubationTime)`  
Définit l'heure de fin d'incubation.

### SetReviewDate
**Signature** : `Logical SetReviewDate(Date NewReviewDate)`  
Fixe la date de relecte/revue du résultat microbiologique.

### TextualSummary
**Signature** : `String TextualSummary(Logical PositiveOnly, PositiveInteger MinimalSeverity, String ViewFormat)`  
Retourne un résumé textuel des résultats microbiologiques.

### LastRequest
**Signature** : `Request LastRequest(Logical Explicit)`  
Retourne la dernière demande associée.

---

## Isolation (isol)

### SetOrganism
**Signature** : `Logical SetOrganism(Mnemonic OrganismMnemonic)`  
Identifie l'organisme de l'isolement.

### SetRIS / ReplaceRIS / ReplaceReportedRIS
```
Logical SetRIS(Mnemonic AntibioticMnemonic, String RISNewValue, Logical Create)
Logical ReplaceRIS(Mnemonic AntibioticMnemonic, String RISOldValue, String RISNewValue)
Logical ReplaceReportedRIS(Mnemonic AntibioticMnemonic, String RISOldReportValue, String RISNewReportValue)
```
Définit/remplace la valeur RIS (Résistant/Intermédiaire/Sensible) pour un antibiotique.

```mispl
/* Forcer résistance pour un antibiotique */
isolement.SetRIS("AMOX", "R", YES);
```

### EqualRIS / EqualReportedRIS
```
Logical EqualRIS(Mnemonic AntibioticMnemonic, String RISValues, Logical MustBeTested)
Logical EqualReportedRIS(Mnemonic AntibioticMnemonic, String RISValues, Logical MustBeTested)
```
Teste si le RIS correspond à une valeur donnée.

### HideRIS
**Signature** : `Logical HideRIS(Mnemonic AntibioticMnemonic, String RISValues)`  
Masque un résultat RIS dans le rapport.

### SetInternalComment / SetExternalComment
```
Logical SetInternalComment(String Value)
Logical SetExternalComment(String Value)
```
Définit les commentaires interne/externe de l'isolement.

### SetReportOfficially
**Signature** : `Logical SetReportOfficially(Logical ReportOfficially)`  
Active/désactive le signalement officiel de l'isolement.

### AntibioticResult
**Signature** : `AntibioticResult AntibioticResult(Mnemonic AntibioticMnemonic)`  
Accède au résultat d'antibiogramme pour un antibiotique spécifique.

### AddTest
**Signature** : `IsolationTest AddTest(Mnemonic TestMnemonic)`  
Ajoute un test à l'isolement.

---

## Carrier (carr)

### AddIsolation / AddIsolationWithAppraisal
```
Logical AddIsolation(Mnemonic OrganismMnemonic)
Logical AddIsolationWithAppraisal(Mnemonic OrganismMnemonic, Mnemonic Appraisal)
```
Ajoute un isolement au milieu de culture, avec ou sans appréciation.

### AddSubCarrier
**Signature** : `Logical AddSubCarrier(String MnemonicList, Logical Print, Logical MarkAsGrafted, Logical Double, String Comment)`  
Ajoute un sous-milieu de culture.

---

## AntibioticResult (abrs)

### AddComment
**Signature** : `Logical AddComment(String Text, Logical Append)`  
Ajoute un commentaire au résultat d'antibiogramme.

### AgarDiffusionValue / ETestValue / MICValue
```
PositiveFractional AgarDiffusionValue()
PositiveFractional ETestValue()
PositiveFractional MICValue()
```
Retournent les valeurs quantitatives de l'antibiogramme (diamètre diffusion, E-test, CMI).

### SetReportable
**Signature** : `Logical SetReportable(Logical NewReportability)`  
Active/désactive l'inclusion du résultat dans le rapport.
