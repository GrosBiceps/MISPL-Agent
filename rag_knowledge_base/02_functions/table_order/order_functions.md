---
id: "functions_table_order"
type: "fonction_core"
domaine: "table_order"
langage_proxy: "Progress ABL / OpenEdge"
context: ["action", "result", "order"]
table_abbrev: "ord"
return_type: "Logical | Result | Specimen"
priority: "critical"
keywords_fr: ["ajouter demande", "ajouter analyse", "créer demande", "déclencher analyse", "imprimer rapport", "post-traitement", "étiquette", "planifier rapport", "accéder résultat du dossier", "dossier", "facturation", "cascade", "reflexe"]
anti_hallucination: ["CreateOrder n'existe pas — AddRequest sur dossier existant", "NewOrder n'existe pas"]
tags: [Order, ord, AddRequest, ScheduleReports, PostProcess, Result, Specimen, CreationTime, ReceiptTime, CreationUser, Discontinue, cancel_reason]
---

# Fonctions de la table Order (Dossier)

Table GLIMS : `ord` — représente un dossier d'analyses (ensemble de demandes pour un patient).  
Accès depuis contexte Result : `.Action().Order()` ou `.Result.Order` ou `Result.Order`.  
Accès depuis contexte Action : `Action.Order()`.

---

## AddRequest
**Signature** : `Logical AddRequest(String RequestMnemonic, Object ObjectOrUnknown, Logical BillingMark)`  
Ajoute une demande d'analyse au dossier.  
- `RequestMnemonic` : mnémonique de l'analyse à ajouter.  
- Paramètre 2 : passer `?` pour utiliser l'objet courant du dossier.  
- `BillingMark` : `YES` pour facturer, `NO` pour ne pas facturer, `?` pour valeur par défaut.

```mispl
/* Ajouter une analyse simple */
Action.Order().AddRequest("PSAL", ?, ?);

/* Ajouter avec facturation */
Action.Order().AddRequest("PSAL", ?, YES);

/* Ajouter plusieurs analyses (pattern TOXO) */
Action.Order().AddRequest("A_S_T_IGG_VIDAS_INFO", ?, ?);
Action.Order().AddRequest("A_S_T_IGM_VIDAS_INFO", ?, ?);
Action.Order().AddRequest("A_S_T_COMMENTAIRE", ?, ?);
```

**ATTENTION** : `AddRequest` sur Order a 3 paramètres. Sur Specimen, la signature diffère légèrement.

---

## CascadeRequest (LEGACY — ne plus utiliser)
**Signature** : `Logical CascadeRequest(String RequestMnemonic)`  
⚠️ **DÉPRÉCIÉ** : `CascadeRequest` appartient à une ancienne version de GLIMS. **Ne jamais le proposer dans du nouveau code.**

**Remplacement obligatoire** : utiliser `Action.Order().AddRequest("MNEM", ?, ?)` ou `Result.Order.AddRequest("MNEM", ?, ?)`.

```mispl
/* ANCIEN (déprécié) : CascadeRequest("B_CALC_CREAT_UR"); */

/* NOUVEAU — toujours utiliser AddRequest */
Action.Order().AddRequest("B_CALC_CREAT_UR", ?, ?);
RETURN YES;
```

Les anciens scripts du CHU contiennent encore `CascadeRequest`, mais tout nouveau script doit utiliser `AddRequest`.

---

## ScheduleReports
**Signature** : `Logical ScheduleReports()`  
Planifie l'édition des rapports pour le dossier courant.  
À appeler après `AddRequest` pour déclencher l'impression automatique.

```mispl
.Action().Order().AddRequest("PSAL", ?, YES);
.Action().Order().ScheduleReports();
```

---

## PostProcess
**Signature** : `Logical PostProcess(Logical p1, Logical p2, Logical p3, Logical p4, Logical p5, Logical p6, Logical p7)`  
Lance le post-traitement du dossier (impression étiquettes, rapports, transmissions...).  
Les 7 paramètres booléens contrôlent les différentes étapes du post-traitement.  
`?` pour valeur par défaut sur un paramètre.

```mispl
/* Imprimer les étiquettes échantillons */
Action.Order().PostProcess(YES, YES, YES, YES, YES, NO, YES);

/* PostProcess avec valeurs par défaut */
Action.Order().PostProcess(?, ?, ?, ?, ?, ?, YES);
```

---

## Result (navigation)
**Signature** : `Result Result(String Mnemonic, String StatusFrom, String StatusTo)`  
Recherche un résultat dans le dossier par mnémonique et plage de statuts.  
Tester `.Id <> ?` pour vérifier l'existence.  
Passer `?` pour ne pas filtrer sur un paramètre de statut.

```mispl
/* Vérifier qu'un résultat B_COB_LACT_SG existe dans le dossier */
IF Action.Order().Result("B_COB_LACT_SG", ?, ?).Id <> ? THEN ...

/* Récupérer un résultat validé spécifique */
.Order.Result("B_MOD_PRO_SG", "Initial", "Validated").Cancel("Discontinue", "Raison");
```

---

## Specimen (navigation)
**Signature** : `Specimen Specimen(Integer Index)`  
Accède au n-ième prélèvement du dossier (base 1).

---

## CreationTime / ReceiptTime (champs)
**Types** : `DateTime`  
Horodatages de création et réception du dossier.

```mispl
DateTimeToDate(Action.Order().ReceiptTime)
DateTimeToString(Action.Order().CreationTime, "%Y/%m/%d")
```

---

## CreationUser (navigation)
**Accès** : `Action.Order().CreationUser.LoginName`  
Accède à l'utilisateur ayant créé le dossier.

```mispl
IF Action.Order().CreationUser.LoginName = "presco" THEN ...
```

---

## Cas d'usage CHU — Ajout multiple de demandes (TOXO)

```mispl
/* B_Ajout A_TOXO : ajouter 4 analyses en une seule fois */
LOGICAL PROGRAM
  Action.Order().AddRequest("A_S_T_IGG_VIDAS_INFO", ?, ?);
  Action.Order().AddRequest("A_S_T_IGM_VIDAS_INFO", ?, ?);
  Action.Order().AddRequest("A_S_T_COMMENTAIRE", ?, ?);
  Action.Order().AddRequest("A_SEROTHEQUE_SUPPORT", ?, ?);
RETURN YES;
```

---

## Cas d'usage CHU — PostProcess pour impression étiquettes

```mispl
/* B_Edition Etiquette dossier */
LOGICAL PROGRAM
  Action.Order().AddRequest("ETIQ", ?, ?);
  Action.Order().PostProcess(?, ?, ?, ?, ?, ?, YES);
RETURN YES;
```
