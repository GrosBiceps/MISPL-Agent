---
id: "functions_result_missing"
type: "fonction_core"
domaine: "result_missing"
langage_proxy: "Progress ABL / OpenEdge"
context: ["result"]
table_abbrev: "rslt"
return_type: "String | Logical | Integer | Object"
priority: "medium"
keywords_fr: ["selection sang resultat", "non-conformite rapportee", "code dilution", "promotion sang", "discontinuation sang"]
anti_hallucination: []
tags: [Result, BloodSelectionDiscontinuation, BloodSelectionPromotion, BloodSelectionReported, GetBloodSelection, GetDilutionCode, ReportedNonconformity]
---


# Fonctions RSLT — complément exhaustif

> Fiches régénérées à partir de faits bruts (signature, retour, effet observable, contraintes), sans reprise de la rédaction du manuel. Méthode : voir `SOURCES.md`.

---

## BloodSelectionDiscontinuation
**Signature** : `Logical BloodSelectionDiscontinuation(String Reason)`  
- **Retour** : `Logical`
- **Paramètres** : 1 — `Reason` (String)
- **Effet** : discontinuation + répétition de la sélection de sang liée (résultat = épreuve de compatibilité) ; motif requis
- **Propriété** : Active

---

## BloodSelectionPromotion
**Signature** : `Logical BloodSelectionPromotion()`  
- **Retour** : `Logical`
- **Paramètres** : 0
- **Effet** : promotion de la sélection de sang liée
- **Propriété** : Active

---

## BloodSelectionReported
**Signature** : `BloodSelection BloodSelectionReported()`  
- **Retour** : `BloodSelection` ; `?` si aucune
- **Paramètres** : 0
- **Effet** : BloodSelection rapportée du résultat

---

## GetBloodSelection
**Signature** : `BloodSelection GetBloodSelection()`  
- **Retour** : `BloodSelection` ; `?` si aucune
- **Paramètres** : 0
- **Effet** : BloodSelection liée au résultat

---

## GetDilutionCode
**Signature** : `DilutionCode GetDilutionCode(String Code)`  
- **Retour** : `DilutionCode` ; `?` si code inconnu
- **Paramètres** : 1 — `Code` (String)
- **Effet** : DilutionCode par code texte ; usage : paramètre de .Dilute()

---

## ReportedNonconformity
**Signature** : `Nonconformity ReportedNonconformity()`  
- **Retour** : `Nonconformity` ; `?` si aucune
- **Paramètres** : 0
- **Effet** : Nonconformity liée, accessible depuis un module de texte de compte rendu (table Result)
