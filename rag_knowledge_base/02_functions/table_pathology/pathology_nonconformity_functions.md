---
id: "functions_table_pathology_nc"
type: "fonction_core"
domaine: "table_pathology_nonconformity"
langage_proxy: "Progress ABL / OpenEdge"
context: ["action", "result"]
table_abbrev: ["ptex", "nc", "enct"]
return_type: "Logical | String | Nonconformity | Encounter"
priority: "medium"
keywords_fr: ["anatomopathologie", "examen anapath", "statut anapath", "valider anapath", "discontinuer anapath", "non-conformité", "enregistrer non-conformité", "contexte NC", "épisode patient", "hospitalisation", "séjour"]
anti_hallucination: []
tags: [PathologyExam, ptex, Nonconformity, nc, Encounter, enct, SetStatus, SetStatusValidated, SetStatusDiscontinued, SetStatusRunning, Reopen, ChangeResponsible, RegisterNonconformity, GetNonconformity, HasStay, FindStay, Close]
---

# Fonctions Anatomopathologie, Non-Conformités, Encounter

---

## PathologyExam (ptex)

Table `ptex` — examen d'anatomopathologie.

### SetStatus
**Signature** : `Logical SetStatus(String StatusName, String ExtraInfo)`  
Change le statut de l'examen par nom.

### SetStatusRunning / SetStatusValidated / SetStatusValidatedComplete
**Signatures** :
```
Logical SetStatusRunning()
Logical SetStatusValidated()
Logical SetStatusValidatedComplete()
Logical SetStatusConfirmed()
Logical SetStatusConfirmedComplete()
Logical SetStatusDiscontinued()
```
Transitions de statut prédéfinies pour les examens anatomopathologiques.

```mispl
/* Valider un examen d'anatomopathologie */
.PathologyExam().SetStatusValidated();
```

### Reopen
**Signature** : `Logical Reopen()`  
Rouvre un examen validé pour modification.

### ChangeResponsible
**Signature** : `Logical ChangeResponsible(Mnemonic Responsible)`  
Change le biologiste/pathologiste responsable de l'examen.

### SetWorkStatus
**Signature** : `Logical SetWorkStatus(String WorkStatusName)`  
Définit le statut de travail interne de l'examen.

---

## Nonconformity (nc)

Table `nc` — non-conformité COFRAC.

### GetContext
**Signature** : `NCContext GetContext(String TableName, PositiveInteger n)`  
Retourne le contexte (enregistrement) lié à la non-conformité.

### RegisterNonconformity (sur SpecificSite/gp_Site)
**Signature** : `Nonconformity RegisterNonconformity(Mnemonic ContextTableName, PositiveInteger ContextRecordId, Mnemonic NCTypeMnemonic)`  
Enregistre une non-conformité sur un enregistrement donné.

```mispl
/* Enregistrer une NC depuis un résultat */
RegisterNonconformity("rslt", .Id, "B_NC_DELAI");
```

### GetNonconformity (sur SpecificSite/gp_Site)
**Signature** : `Nonconformity GetNonconformity(Mnemonic ContextTableName, PositiveInteger ContextRecord, String NCTypeMnemonic, Integer Nonconformity)`  
Recherche une non-conformité existante.

---

## Encounter (enct)

Table `enct` — épisode de soin / hospitalisation.

### Close
**Signature** : `Logical Close(DateTime TargetTime)`  
Clôture l'épisode de soin à la date spécifiée.

### FindContract
**Signature** : `Contract FindContract(DateTime TargetTime)`  
Cherche le contrat d'assurance actif à la date.

### FindStay
**Signature** : `Stay FindStay(DateTime TargetTime)`  
Retourne le séjour actif dans l'épisode à la date donnée.

### GetDiagnosis
**Signature** : `Diagnosis GetDiagnosis(Diagnosis Previous, String Code)`  
Itère sur les diagnostics de l'épisode.

### HasStay
**Signature** : `Logical HasStay(DateTime ReferenceTime, String WardMnemonicList)`  
Teste si l'épisode inclut un séjour dans un service de la liste à l'heure de référence.

```mispl
/* Vérifier si le patient est en réanimation */
IF .Encounter.HasStay(Now(), "REANIMATION,SOINS_INTENSIFS") THEN
  .AddInternalComment("Patient en unité critique", YES);
ENDIF;
```
