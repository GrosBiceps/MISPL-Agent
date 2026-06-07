---
id: "syntax_patterns_courants"
type: "syntaxe_core"
domaine: "patterns_courants"
langage_proxy: "Progress ABL / OpenEdge"
context: ["all"]
table_abbrev: null
return_type: null
priority: "critical"
keywords_fr: ["pattern reflex", "tester valeur connue", "vérifier si résultat existe", "boucle while", "itérer", "liste délimitée", "accumuler chaîne", "IF THEN ELSE ENDIF", "déclarer variable", "initialiser variable", "tester type objet", "test garde", "annuler résultat existant", "lancer plusieurs demandes", "comment structurer script", "structure programme type", "alerte critique", "sévérité critique", "envoyer email rôle", "SendMail rôle", "GetRole", "age patient seuil", "NumericValue seuil", "AddInternalComment certaine", "sc_Role SendMail certaine"]
anti_hallucination: ["RETURN doit être la dernière instruction du programme", "Les variables se déclarent AVANT toute instruction exécutable", "WHILE boucle se ferme avec DONE pas END", "REPEAT boucle se ferme avec UNTIL", "AgeInYears s'accède via .Action().Object.AgeInYears(Today()) depuis Result — PAS .Action().Order().Specimen.Object.AgeInYears()", "AddInternalComment EXISTE et est certaine — ne jamais marquer à vérifier", "sc_Role.SendMail EXISTE via GetRole('MNEM').SendMail(...) — ne jamais marquer à vérifier"]
tags: [pattern, reflex, test, boucle, WHILE, DONE, REPEAT, UNTIL, IF, THEN, ELSE, ENDIF, declaration, initialisation, structure, AddRequest, NumericValue, Mantissa, MarkAsSolicited, AddInternalComment, SetManualSeverity, GetRole, sc_Role, SendMail, AgeInYears, alerte_critique, email_role]
---

# Patterns MISPL courants — structures de référence

---

## Pattern 1 : Reflex test — déclencher si valeur dans une plage

Structure canonique pour déclencher une analyse complémentaire selon la valeur d'un résultat.

```mispl
LOGICAL PROGRAM
  /* 1. Toujours déclarer les variables en tête */
  STRING valeur;

  /* 2. Lire la valeur brute (gère les qualificatifs < >) */
  valeur := .Result.Attribute("Value");

  /* 3. Marquer comme sollicité AVANT le test */
  .Result.MarkAsSolicited();

  /* 4. Tester la plage numérique */
  IF StringToFractional(valeur) >= 3.5 AND StringToFractional(valeur) < 10 THEN
    .Action().Order().AddRequest("PSAL", ?, YES);
    .AddInternalComment("PSAL déclenché automatiquement", YES);
  ENDIF;

RETURN YES;
```

---

## Pattern 2 : Tester si valeur connue (non ?)

```mispl
/* Mantissa = champ décimal brut — plus rapide que StringToFractional */
IF .Result.Mantissa <> ? THEN
  Action.Order().AddRequest("B_COMM_AMH", ?, ?);
ENDIF;

/* NumericValue = méthode — gère les qualificatifs automatiquement */
IF .NumericValue() <> ? AND .NumericValue() >= 0 THEN
  .SetManualSeverity(3);
ENDIF;
```

---

## Pattern 3 : Vérifier type objet avant d'agir

```mispl
LOGICAL PROGRAM
  STRING typeObj;
  typeObj := EnumeratedToString("ObjectType", Action.ObjectType);
  IF typeObj = "person" THEN
    IF .Result.Mantissa <> ? THEN
      Action.Order().AddRequest("B_TRAITEMENT_HUMAIN", ?, ?);
    ENDIF;
    RETURN YES;
  ELSE
    RETURN NO;   /* Animaux ou devices → ne rien faire */
  ENDIF;
```

---

## Pattern 4 : Vérifier si un résultat existe dans le dossier

```mispl
/* Méthode 1 : IsRequested — plus lisible */
IF Action.Order().IsRequested("B_COB_LACT_SG", NO) THEN
  .SetManualSeverity(3);
ENDIF;

/* Méthode 2 : Result.Id — plus précis (filtre statut) */
IF Action.Order().Result("B_COB_LACT_SG", ?, ?).Id <> ? THEN
  Action.Order().AddRequest("B_COMM_CRITIQUE", ?, ?);
ENDIF;
```

---

## Pattern 5 : Utiliser deux résultats liés

```mispl
LOGICAL PROGRAM
  /* Vérifier que les deux résultats liés ont une valeur avant calcul */
  IF StringToFractional(.Result.RelatedResult("B_VOLUME_UR").Attribute("Value")) <> ?
    AND StringToFractional(.Result.RelatedResult("B_TEMPS_RECUEIL").Attribute("Value")) <> ?
  THEN
    Action.Order().AddRequest("B_CALC_CREAT_UR", ?, ?);
  ENDIF;
RETURN YES;
```

---

## Pattern 6 : Boucle sur liste délimitée

```mispl
LOGICAL PROGRAM
  STRING liste, element;
  INTEGER i, nb;

  liste := "B_PSA,B_PSAL,B_FPSA,B_COMM_PSA";
  nb := NumEntries(liste, ",");

  i := 1;
  WHILE i <= nb DO
    element := Entry(i, liste, ",");
    IF NOT Action.Order().IsRequested(element, NO) THEN
      Action.Order().AddRequest(element, ?, ?);
    ENDIF;
    i := i + 1;
  DONE;

RETURN YES;
```

---

## Pattern 7 : Condition garde (nuit / week-end / férié)

```mispl
LOGICAL PROGRAM
  LOGICAL enGarde;
  INTEGER jourSemaine;
  STRING heure;

  enGarde := NO;
  jourSemaine := Lookup(
    DateTimeToString(Action.Order().ReceiptTime, "%a"),
    "lun,mar,mer,jeu,ven,sam,dim", ""
  );
  heure := DateTimeToString(Action.Order().ReceiptTime, "%H:%M");

  IF IsHoliday(DateTimeToDate(Action.Order().ReceiptTime)) OR jourSemaine = 7 THEN
    enGarde := YES;
  ENDIF;
  IF jourSemaine = 6 AND (heure <= "08:00" OR heure >= "12:00") THEN
    enGarde := YES;
  ENDIF;
  IF jourSemaine <= 5 AND (heure <= "08:00" OR heure >= "18:00") THEN
    enGarde := YES;
  ENDIF;

  IF enGarde THEN
    Result.SetManualSeverity(500);
    Result.validate();
  ELSE
    Result.SetManualSeverity(0);
  ENDIF;

RETURN YES;
```

---

## Pattern 8 : Annuler un résultat existant puis en créer un nouveau

```mispl
LOGICAL PROGRAM
  /* Annuler si résultat existant validé */
  IF .Result.Order.Result("B_MOD_PRO_SG", "Initial", "Validated").RawValue <> ? THEN
    .Result.Order.Result("B_MOD_PRO_SG", "Initial", "Validated")
      .Cancel("Discontinue", "Remplacé par protéine sérique");
  ENDIF;

  /* Créer la nouvelle demande */
  .Result.Order.AddRequest("B_PRO_SERIQUE", ?, ?);

RETURN YES;
```

---

## Pattern 9 : Sévérité conditionnelle sur plage

```mispl
LOGICAL PROGRAM
  /* Sévérité selon valeur — 0=normal, >0=alerte */
  IF .Result.NumericValue() <= 1 OR .Result.NumericValue() >= 500 THEN
    .Result.SetManualSeverity(11);   /* critique */
  ELSE
    .Result.SetManualSeverity(0);    /* normal */
  ENDIF;
RETURN YES;
```

---

## Pattern 10 : Ajouter plusieurs demandes en une fois

```mispl
LOGICAL PROGRAM
  /* Pattern multi-AddRequest — sérologie TOXO */
  Action.Order().AddRequest("A_TOXO_IGG", ?, ?);
  Action.Order().AddRequest("A_TOXO_IGM", ?, ?);
  Action.Order().AddRequest("A_TOXO_COMMENT", ?, ?);
  Action.Order().ScheduleReports();
RETURN YES;
```

---

## Règles syntaxiques à ne jamais violer

| Règle | Correct | INCORRECT |
|-------|---------|-----------|
| Déclarations en tête | `STRING v; v := ...;` | `v := ...; STRING v;` ❌ |
| RETURN obligatoire | `RETURN YES;` | *(absent)* ❌ |
| Fermeture boucle | `WHILE ... DO ... DONE;` | `WHILE ... DO ... END;` ❌ |
| Fermeture IF | `IF ... THEN ... ENDIF;` | `IF ... THEN ... END;` ❌ |
| Division entière | `321.0 / 60` | `321 / 60` → tronqué ⚠️ |
| Valeur inconnue | `IF x <> ? THEN` | `IF x <> NULL THEN` ❌ |

---

## Pattern 11 : Alerte critique — sévérité + commentaire interne + email rôle de garde

Pattern complet combinant : NumericValue, AgeInYears, SetManualSeverity, AddInternalComment, GetRole + SendMail.
**AddInternalComment et sc_Role.SendMail sont des fonctions CERTAINES — ne jamais les mettre en pseudo-code.**

```mispl
LOGICAL PROGRAM
  /* Stocker les valeurs pour éviter les accès BD répétés */
  FRACTIONAL val;
  FRACTIONAL age;
  sc_Role roleGarde;

  val := .NumericValue();
  /* Navigation correcte depuis Result : .Action().Object — PAS .Action().Order().Specimen.Object */
  age := .Action().Object.AgeInYears(Today());

  /* Tester les valeurs inconnues en tête */
  IF val = ? OR age = ? THEN
    RETURN NO;
  ENDIF;

  IF val < 50.0 AND age > 65.0 THEN
    /* 1. Fixer la sévérité critique */
    .SetManualSeverity(11);

    /* 2. Commentaire interne — AddInternalComment est CERTAINE, toujours disponible */
    .AddInternalComment("Thrombopenie severe chez patient age — avis biologiste requis", YES);

    /* 3. Email au rôle de garde — GetRole().SendMail() est CERTAINE */
    roleGarde := GetRole("BIOLOGISTE_GARDE");
    IF roleGarde <> ? THEN
      roleGarde.SendMail(
        "Alerte thrombopenie",
        "Thrombopenie severe detectee. Valeur : " + FractionalToString(val, "%g") + " G/L. Patient > 65 ans.",
        MailPriority["High"]
      );
    ENDIF;
  ENDIF;

RETURN YES;
```

**Fonctions utilisées (toutes CERTAINES, ne jamais marquer à vérifier) :**
- `NumericValue()` — valeur numérique du résultat
- `.Action().Object.AgeInYears(Today())` — âge patient depuis contexte Result
- `SetManualSeverity(n)` — sévérité manuelle
- `AddInternalComment(Text, Append)` — commentaire interne
- `GetRole("MNEM")` — récupérer un rôle par son mnémonique
- `sc_Role.SendMail(Subject, Content, Priority)` — email à tous les utilisateurs du rôle
- `FractionalToString(val, "%g")` — convertir décimal en chaîne pour le message
- `MailPriority["High"]` — priorité email haute
