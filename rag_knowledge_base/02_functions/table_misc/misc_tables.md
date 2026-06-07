---
id: "functions_misc_tables"
type: "fonction_core"
domaine: "tables_diverses"
langage_proxy: "Progress ABL / OpenEdge"
context: ["all"]
table_abbrev: ["rqst", "stn", "wlst", "stdy", "rqbl", "os"]
return_type: "String | Logical | Integer | Order | Request"
priority: "medium"
keywords_fr: ["demande analyse tarif", "imprimer étiquettes station", "liste travail analyseur", "statut action liste", "étude cohorte prochain dossier", "panel analyses", "données dossier facturation", "OrderSet données"]
anti_hallucination: ["Station est un objet GLIMS distinct de l'analyseur physique"]
tags: [Request, rqst, Station, stn, WorkList, wlst, Study, stdy, Requestable, rqbl, OrderSet, os, DefaultTariff, GetStationEventCode, ActionStatus, GetNextOrder, GetPanelRequestable, OrderData, LinkedOrder]
---

# Fonctions des tables Request, Station, WorkList, Study, Requestable, OrderSet

---

## DefaultTariff (rqst — Request)
**Signature** : `String DefaultTariff()`  
Retourne le code tarif par défaut associé à cette demande d'analyse.

```mispl
/* Lire le tarif par défaut d'une demande */
STRING tarif;
tarif := .Request.DefaultTariff();
```

---

## DefaultTariffInfo (rqst — Request)
**Signature** : `String DefaultTariffInfo()`  
Retourne des informations détaillées sur le tarif par défaut de la demande.

---

## GetStationEventCode (stn — Station)
**Signature** : `String GetStationEventCode(String EventMnemonic)`  
Retourne le code événement configuré pour un mnémonique d'événement sur la station analyseur.  
Utilisé pour déclencher des actions spécifiques à un analyseur (impression étiquette, transfert résultat).

```mispl
/* Déclencher un événement sur la station courante */
STRING code;
code := .Station.GetStationEventCode("PRINT_LABEL");
```

---

## ActionStatus (wlst — WorkList)
**Signature** : `String ActionStatus(Mnemonic ActionMnemonic)`  
Retourne le statut d'une action spécifique sur la liste de travail.  
Permet de vérifier si une analyse est en attente, en cours ou terminée sur un analyseur.

```mispl
/* Vérifier le statut d'une analyse sur la liste de travail */
STRING statut;
statut := .WorkList.ActionStatus("B_PSA");
/* ex: "Pending", "Running", "Done" */
```

---

## GetNextOrder (stdy — Study)
**Signature** : `Order GetNextOrder(Order Previous)`  
Itère sur les dossiers d'une étude/cohorte. `Previous = ?` pour commencer au premier.

```mispl
/* Parcourir tous les dossiers d'une étude */
Order dossier;
dossier := .Study.GetNextOrder(?);
WHILE dossier.Id <> ? DO
  /* traiter chaque dossier de l'étude */
  dossier := .Study.GetNextOrder(dossier);
DONE;
```

---

## GetNextStudyObject (stdy — Study)
**Signature** : `Object GetNextStudyObject(Object Previous)`  
Itère sur les objets (patients) inclus dans une étude. `Previous = ?` pour commencer.

```mispl
/* Parcourir les patients d'une cohorte */
Object patient;
patient := .Study.GetNextStudyObject(?);
WHILE patient.Id <> ? DO
  patient := .Study.GetNextStudyObject(patient);
DONE;
```

---

## GetPanelRequestable (rqbl — Requestable)
**Signature** : `Requestable GetPanelRequestable(Mnemonic PanelMnemonic)`  
Retourne l'analyse associée à un panel (groupe d'analyses) par son mnémonique.

```mispl
/* Accéder à une analyse d'un panel */
Requestable analyse;
analyse := .Requestable.GetPanelRequestable("B_BILAN_HEPATIQUE");
```

---

## Tariff (rqbl — Requestable)
**Signature** : `String Tariff(Mnemonic FirmMnemonic, Date ValidityDate)`  
Retourne le code tarif de l'analyse pour une firme et une date de validité données.

---

## OrderData (os — OrderSet)
**Signature** : `String OrderData(String TaggedParameterList)`  
Retourne des données formatées sur les dossiers de l'ensemble OrderSet selon une liste de paramètres taguée.

---

## LinkedOrder (os — OrderSet)
**Signature** : `Order LinkedOrder(Order Previous)`  
Itère sur les dossiers liés dans un OrderSet. `Previous = ?` pour commencer.

---

## BillingCodesCurrentlyPresent (os — OrderSet)
**Signature** : `String BillingCodesCurrentlyPresent(String BillingCodeList)`  
Retourne la liste des codes de cotation actuellement présents dans l'OrderSet.

---

## FrenchSupplements (os — OrderSet)
**Signature** : `String FrenchSupplements(...)`  
Calcule les suppléments tarifaires France (spécifique nomenclature française — NABM, NGAP).

```mispl
/* Calculer les suppléments French NABM */
STRING suppl;
suppl := .OrderSet.FrenchSupplements(?);
```
