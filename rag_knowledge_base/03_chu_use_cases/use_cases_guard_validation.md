---
id: "usecase_garde_validation"
type: "cas_usage_production"
domaine: "validation_automatique_garde"
langage_proxy: "Progress ABL / OpenEdge"
context: ["result", "action"]
table_abbrev: ["rslt", "ord", "actn"]
return_type: "Logical"
priority: "high"
keywords_fr: ["garde", "validation automatique", "COFRAC", "nuit", "week-end", "biologiste", "responsable de garde", "IsHoliday", "LookUp jour", "plage horaire", "valider résultat", "revue dossier", "SetManualSeverity", "GetSiteAttribute", "IfKnownString", "Status", "validate"]
anti_hallucination: ["Result.validate() est une méthode valide", "Result.Status est un champ entier (5 = validé)", ".ResultAttribute est une abréviation valide de .Result.Attribute", "GetSiteAttribute peut prendre 3 paramètres"]
source: "fonctions_mispl.xlsx — Production CHU"
tags: [garde, IsHoliday, LookUp, DateTimeToString, validate, Status, GetSiteAttribute, IfKnownString, SetManualSeverity, AddRequest, Cancel, COFRAC, nuit, weekend]
---

# Cas d'usage : Validation automatique en garde et COFRAC

---

## UC-GUARD-01 : Détection garde + validation conditionnelle (B_non_conf_en_garde)

**Contexte** : Result. Script COFRAC complet — détermine si la réception est en garde (nuit/week-end/férié) et adapte la sévérité et la demande de revue.

**Fonctions clés** : `DateTimeToDate`, `LookUp`, `DateTimeToString`, `IsHoliday`, `AddRequest`, `SetManualSeverity`, `validate`

```mispl
/* COFRAC — Validation différenciée garde/hors garde */
LOGICAL PROGRAM
  LOGICAL Rep;
  DATE Jour;
  INTEGER WeekDay, l;
  STRING Reception, ListeLabo, Labo_Garde, Labo;

  /* Initialisation */
  Rep := NO;

  /* Extraction date et heure de réception du dossier */
  Jour := DateTimeToDate(Action.Order().ReceiptTime);

  /* LookUp retourne position (1=lun ... 7=dim), "" = délimiteur vide → espace */
  WeekDay := LookUp(DateTimeToString(Action.Order().ReceiptTime, "%a"),
                    "lun,mar,mer,jeu,ven,sam,dim", "");
  Reception := DateTimeToString(Action.Order().ReceiptTime, "%H:%M");

  /* Test garde dimanche ou férié */
  IF IsHoliday(Jour) OR WeekDay = 7 THEN
    Rep := YES;
  ENDIF;

  /* Test garde samedi (uniquement hors plage 08:00-12:00) */
  IF WeekDay = 6 AND (Reception <= "08:00" OR Reception >= "12:00") THEN
    Rep := YES;
  ENDIF;

  /* Test garde semaine (hors plage 08:00-18:00) */
  IF WeekDay <= 5 AND (Reception <= "08:00" OR Reception >= "18:00") THEN
    Rep := YES;
  ENDIF;

  /* Actions selon contexte garde */
  IF Rep THEN
    /* En garde : demande de revue dossier + sévérité de garde */
    Result.Order.AddRequest("B_REVUE", ?, ?);
    Result.SetManualSeverity(500);
    Result.validate();      /* validation automatique en garde */
  ELSE
    /* Hors garde : sévérité normale */
    Result.SetManualSeverity(600);
  ENDIF;

RETURN YES;
```

**Points notables** :
- `LookUp` avec délimiteur `""` (chaîne vide) → utilise le délimiteur espace par défaut
- `Reception <= "08:00"` → comparaison lexicographique de chaînes HH:MM — fonctionne si format constant
- `Result.validate()` — méthode de validation directe, minuscules = majuscules

---

## UC-GUARD-02 : Gestion biologiste responsable + revue complexe (B_Valid_Bio_garde)

**Contexte** : Result. Lit le biologiste responsable depuis un attribut de site, gère la revue et la transmission de responsabilité.

**Fonctions clés** : `GetSiteAttribute`, `IfKnownString`, `Result.Status`, `Cancel`, `AddRequest`

```mispl
/* COFRAC — Analyse sans bornes, validation conditionnelle selon garde */
LOGICAL PROGRAM
  STRING MaDiscipline, AnaRevue, AnaResponsable, VarResponsable;
  STRING MonOldResponsable, MonResponsable;

  /* Construction des noms d'analyse par concaténation */
  MaDiscipline := "B";
  AnaRevue := MaDiscipline + "_REVUE";           /* "B_REVUE" */
  AnaResponsable := MaDiscipline + "_NUIT_FERIE"; /* "B_NUIT_FERIE" */
  VarResponsable := MaDiscipline + "_Biologiste"; /* "B_Biologiste" */

  /* Tester si un biologiste de garde est enregistré */
  IF .Result.Order.Result(AnaResponsable, ?, ?).Id <> ? THEN

    /* Récupérer la valeur courante du responsable dans le résultat existant */
    /* IfKnownString n'a qu'un paramètre — retourne "" si inconnu */
    MonOldResponsable := IfKnownString(
      .Result.Order.Result(AnaResponsable, ?, ?).Attribute("Value"));

    /* Lire le biologiste responsable depuis la configuration du site */
    /* GetSiteAttribute avec 3 paramètres : SiteCode, Filtre, NomAttribut */
    MonResponsable := GetSiteAttribute("SpecificSite", ?, VarResponsable);

    /* Gérer la revue : si déjà validée → rouvrir, sinon créer */
    IF .Result.Order.Result(AnaRevue, ?, ?).Status = 5 THEN
      /* Status 5 = Validé — annuler pour remettre en revue */
      .Result.Order.Result(AnaRevue, ?, ?).Cancel("Repeat", "Revue à refaire");
    ELSE
      .Result.Order.AddRequest(AnaRevue, ?, ?);
    ENDIF;

  ENDIF;

RETURN YES;
```

**Points notables** :
- `IfKnownString(valeur)` — retourne `""` si `valeur = ?` (1 seul paramètre, pas de Default)
- `GetSiteAttribute("SpecificSite", ?, VarResponsable)` — forme à 3 paramètres pour site nommé
- `Result.Status = 5` — comparaison directe de la valeur entière de statut

---

## UC-GUARD-03 : Pattern complet B_NC_DETAIL avec listes imbriquées

**Contexte** : Action/Result. Gestion complète des non-conformités avec 5 catégories et listes de détails.

**Fonctions clés** : `Entry`, `NumEntries`, `Lookup`, `LookUp` (insensible casse), concaténation STRING

```mispl
/* Squelette simplifié B_NC_DETAIL */
LOGICAL PROGRAM
  STRING Causes, MaListe, Liste1, Liste2, Liste3, Liste4, Liste5, MonDetail;
  INTEGER LaCause, LeDetail;
  /* ATTENTION : toutes déclarations avant toute instruction */

  Causes := "Prescription|Acheminement|Identification echantillon|Echantillon|Conditionnement";

  /* Chaque liste contient les détails de la cause correspondante */
  Liste1 := "Consentement_non_signe," + "Analyses_non_cochees," +
            "Prescripteur_non_identifie," + "Prescripteur_illisible";

  /* Déterminer la cause (index 1-5) par AskChoice interactif ou paramètre */
  LaCause := AskChoice("Cause de non-conformité ?", "NC",
                       Replace(Causes, "|", ","), YES, 1);

  /* Sélectionner la liste de détails correspondante */
  IF LaCause = 1 THEN MaListe := Liste1; ENDIF;
  IF LaCause = 2 THEN MaListe := Liste2; ENDIF;
  /* etc. */

  /* AskChoice sur les détails */
  LeDetail := AskChoice("Détail ?", "NC", MaListe, YES, 1);
  MonDetail := Entry(LeDetail, MaListe, ",");

RETURN YES;
```

---

## Appendice : `.ResultAttribute` — forme abrégée documentée CHU

Le script `B_Ajout B_BM_MICROSAT` (production CHU) utilise :
```mispl
string valeur;
valeur := .ResultAttribute("Value");    /* forme abrégée valide */
```

Cette notation est fonctionnellement identique à :
```mispl
valeur := .Result.Attribute("Value");   /* forme explicite */
```

Les deux formes sont acceptées par le compilateur GLIMS MISPL.
