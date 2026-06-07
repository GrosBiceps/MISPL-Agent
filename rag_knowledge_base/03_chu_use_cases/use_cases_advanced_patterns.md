---
id: "usecase_patterns_avances"
type: "cas_usage_production"
domaine: "patterns_complexes"
langage_proxy: "Progress ABL / OpenEdge"
context: ["action", "result"]
table_abbrev: ["ord", "rslt", "actn"]
return_type: "Logical"
priority: "high"
keywords_fr: ["non-conformité", "liste dynamique", "garde", "week-end", "jour férié", "utilisateur", "date bascule", "annuler plusieurs", "valeur codée", "valeur textuelle", "accolades", "impossible", "interdit", "CreatePerson"]
anti_hallucination: ["CreatePerson impossible", "ResultAttribute n'existe pas → Result.Attribute", "déclarations variables obligatoirement en tête de programme avant toute instruction"]
source: "fonctions_mispl.xlsx — Production CHU"
tags: [variables, Entry, NumEntries, Lookup, LookUp, DateTimeToString, DateTimeToDate, CurrentUser, CurrentDepartment, IsHoliday, StringToDate, Cancel, RawValue, AddRequest, non_conformite, garde]
---

# Cas d'usage : Patterns avancés

---

## UC-ADV-01 : Gestion des non-conformités avec listes dynamiques

**Contexte** : Action/Result. Utilisation intensive de variables STRING, Entry, NumEntries pour construire des listes de causes/détails.

```mispl
LOGICAL PROGRAM
  /* Toutes les déclarations OBLIGATOIREMENT avant la première instruction */
  STRING Causes, MaListe, Liste1, Liste2;
  INTEGER LaCause, LeDetail, i;

  /* Construction de listes délimitées par | */
  Causes := "Prescription|Acheminement|Identification echantillon|Echantillon";
  Liste1 := "Consentement_non_signe," + "Analyses_non_cochees," + "Prescripteur_non_identifie";

  /* Itération : index commence à 1 (base 1 en MISPL) */
  i := 1;
  WHILE i <= NumEntries(Causes, "|") DO
    /* Entry(i, Causes, "|") retourne le i-ème élément */
    i := i + 1;
  DONE;
RETURN YES;
```

**Fonctions clés** : `NumEntries`, `Entry`, concaténation STRING avec `+`

---

## UC-ADV-02 : Test jour de garde (week-end/férié) avec LookUp + DateTimeToString

**Contexte** : Action. Détermine si la réception est en garde selon le jour de la semaine.

```mispl
LOGICAL PROGRAM
  LOGICAL Rep;
  DATE Jour;
  INTEGER WeekDay;
  STRING Reception;

  Rep := NO;
  Jour := DateTimeToDate(Action.Order().ReceiptTime);
  WeekDay := LookUp(DateTimeToString(Action.Order().ReceiptTime, "%a"),
                    "lun,mar,mer,jeu,ven,sam,dim", ",");
  Reception := DateTimeToString(Action.Order().ReceiptTime, "%H:%M");

  /* WeekDay 1-5 = jours ouvrés, 6-7 = week-end */
  IF WeekDay >= 6 OR IsHoliday(Jour) THEN
    Rep := YES;
  ENDIF;

  /* Vérifier aussi les plages horaires en semaine */
  /* ... */
RETURN Rep;
```

**Fonctions clés** : `DateTimeToDate`, `DateTimeToString`, `LookUp`, `IsHoliday`

---

## UC-ADV-03 : Exécution conditionnelle selon utilisateur courant

**Contexte** : Action. Restreindre une action à certains utilisateurs ou disciplines.

```mispl
LOGICAL PROGRAM
  IF CurrentUser() = "admin" OR CurrentDepartment() = "BIOCHIMIE" THEN
    Action.Order().AddRequest("B_COMM_SPECIAL", ?, ?);
  ENDIF;
RETURN YES;
```

---

## UC-ADV-04 : Déclencheur conditionnel avec date de bascule

**Contexte** : Action. Activer un comportement uniquement à partir d'une date définie.

```mispl
LOGICAL PROGRAM
  IF DateTimeToDate(Action.Order().CreationTime) >= StringToDate("13/02/2017") THEN
    /* Nouveau comportement post-migration */
    Action.Order().AddRequest("B_NOUVEAU_CALCUL", ?, ?);
  ELSE
    /* Ancien comportement */
    Action.Order().AddRequest("B_ANCIEN_CALCUL", ?, ?);
  ENDIF;
RETURN YES;
```

---

## UC-ADV-05 : Annulation en cascade de résultats liés

**Contexte** : Result. Annuler plusieurs résultats liés quand une condition est remplie.

```mispl
LOGICAL PROGRAM
  IF .Result.Order.Result("B_VR_EPR_JEUNE1", "Initial", "Validated").RawValue <> ? THEN
    .Result.Order.Result("B_VR_PANEL_CETONEMIE", "Initial", "Validated")
      .Cancel("Discontinue", "VR Epreuve de jeune supprime VR cétonémie");
    .Result.Order.Result("B_VR_RAP_LAC_PYR", "Initial", "Validated")
      .Cancel("Discontinue", "VR Epreuve de jeune supprime ratio lac/pyr");
  ENDIF;
RETURN YES;
```

---

## UC-ADV-06 : Déclencheur conditonnel avec Attribute("Value") = valeur codée

**Contexte** : Result. Comparer la valeur textuelle (résultat qualitatif) pour déclencher.

```mispl
/* B_BM_CST : si résultat = "Non", créer non-conformité */
LOGICAL PROGRAM
  IF .Result.Attribute("Value") = "Non" THEN
    .Result.Order.AddRequest("B_NON_CONF_CST", ?, ?);
  ENDIF;
RETURN YES;
```

---

## UC-ADV-07 : Déclencheur avec valeur codée entre accolades

**Contexte** : Result. Valeur d'un résultat codé par mnémonique entre accolades.

```mispl
/* B_Ajout B_BM_MICROSAT : si résultat = code {O} (valeur codée par mnémonique) */
LOGICAL PROGRAM
  STRING valeur;
  valeur := .Result.Attribute("Value");    /* .Result.Attribute, pas .ResultAttribute */
  IF valeur = "{O}" THEN
    Action.Order().AddRequest("B_BM_MICROSAT", ?, ?);
    Action.Order().PostProcess(YES, YES, YES, YES, YES, NO, YES);
  ENDIF;
RETURN YES;
```

---

## UC-ADV-08 : Anti-pattern — ce qui est IMPOSSIBLE en MISPL

```mispl
/* IMPOSSIBLE - NE PAS FAIRE : */

/* 1. Créer un nouveau patient */
/* CreatePerson("NOM", "PRENOM", "01/01/2000") -- N'EXISTE PAS */

/* 2. Modifier les valeurs de référence */
/* SetReferenceRange("PSA", 0, 4) -- N'EXISTE PAS */

/* 3. Modifier la configuration GLIMS */
/* SetAnalyteUnit("PSA", "ng/mL") -- N'EXISTE PAS */

/* 4. Utiliser des fonctions VBA/Excel */
/* Left("abc", 2)  -- N'EXISTE PAS, utiliser Substr("abc", 1, 2) */
/* Length("abc")   -- N'EXISTE PAS, utiliser Len("abc") */
/* LCase("ABC")    -- N'EXISTE PAS, utiliser ToLower("ABC") */
/* Val("3.14")     -- N'EXISTE PAS, utiliser StringToFractional("3.14") */
```
