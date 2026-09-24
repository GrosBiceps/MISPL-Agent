---
id: "functions_specimen_missing"
type: "fonction_core"
domaine: "specimen_missing"
langage_proxy: "Progress ABL / OpenEdge"
context: ["action", "result"]
table_abbrev: "spmn"
return_type: "String | Logical | Integer | Object"
priority: "medium"
keywords_fr: ["blocs histologie", "niveau remplacement prelevement", "sortie prelevement", "cotation prelevement"]
anti_hallucination: []
tags: [Specimen, AddBlocks, SetReplacementLevel, SpecimenOutput, TariffResult]
---


# Fonctions SPMN — complément exhaustif

> Fiches régénérées à partir de faits bruts (signature, retour, effet observable, contraintes), sans reprise de la rédaction du manuel. Méthode : voir `SOURCES.md`.

---

## AddBlocks
**Signature** : `PositiveInteger AddBlocks(Mnemonic MediumMnemonic, PositiveInteger NumberToAdd, PositiveInteger NumberToReach, Logical PrintBlockLabel)`  
- **Retour** : `PositiveInteger`
- **Paramètres** : 4 — `MediumMnemonic` (Mnemonic), `NumberToAdd` (PositiveInteger), `NumberToReach` (PositiveInteger), `PrintBlockLabel` (Logical)
- **Effet** : ajout de blocs (milieu, nombre à ajouter ou à atteindre, étiquette) ; retour = nombre de blocs
- **Propriété** : Active

---

## SetReplacementLevel
**Signature** : `Void SetReplacementLevel(PositiveInteger Level)`  
- **Retour** : aucun (`Void`)
- **Paramètres** : 1 — `Level` (PositiveInteger)
- **Effet** : écriture du niveau de remplacement
- **Propriété** : Active

---

## SpecimenOutput
**Signature** : `SpecimenOutput SpecimenOutput()`  
- **Retour** : `SpecimenOutput`
- **Paramètres** : 0
- **Effet** : SpecimenOutput de l'échantillon

---

## TariffResult
**Signature** : `Result TariffResult(String BillingCode, String PropertyMnemonic)`  
- **Retour** : `Result` ; `?` si aucun
- **Paramètres** : 2 — `BillingCode` (String), `PropertyMnemonic` (String)
- **Effet** : Result tarifé (code de facturation, analyse)
- **Contrainte** : uniquement pendant la tarification
