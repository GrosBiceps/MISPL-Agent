---
id: "syntax_contextes_execution"
type: "syntaxe_core"
domaine: "contexte_execution"
langage_proxy: "Progress ABL / OpenEdge"
context: ["result", "action", "order"]
table_abbrev: null
return_type: null
priority: "critical"
keywords_fr: ["contexte", "point", "implicite", "naviguer", "résultat courant", "dossier", "action courante", "chaînage", "accès patient", "accès prélèvement"]
anti_hallucination: []
tags: [contexte, result, order, action, self, point, implicite, navigation, chaining, Action.Order, Result.Order, AgeInYears]
---

# Contextes d'exécution MISPL

## Concept fondamental

En Progress ABL, `THIS-OBJECT:` désigne l'instance courante d'un objet.  
En MISPL, le symbole **`.`** (point seul) désigne l'enregistrement courant du contexte d'exécution.  
La nature de cet enregistrement dépend du **type de texte MISPL** configuré dans GLIMS.

## Les trois contextes principaux

### Contexte Résultat (`.Result` implicite)

Le script est attaché à un résultat d'analyse. Le point `.` représente le **Result courant**.

```mispl
.NumericValue()           /* valeur numérique du résultat courant */
.Attribute("Value")       /* valeur brute (string) */
.MarkAsSolicited()        /* marquer comme sollicité */
.SetManualSeverity(3)     /* fixer la sévérité manuellement */
.Action()                 /* accéder à l'Action parente */
.Action().Order()         /* accéder au Dossier (Order) */
.Action().Order().AddRequest("MNEM", ?, ?)  /* ajouter une demande */
```

### Contexte Action (`.Action` implicite)

Le script est attaché à une Action. Le point `.` représente l'**Action courante**.

```mispl
Action.Order()            /* dossier rattaché à l'action */
Action.ObjectType         /* type de l'objet (person, etc.) */
Action.Order().AddRequest("MNEM", ?, ?)
Action.Order().PostProcess(YES, YES, YES, YES, YES, NO, YES)
```

### Contexte Dossier (`.Order` implicite)

Le script est attaché directement à un Order. Moins fréquent.

```mispl
.AddRequest("MNEM", ?, ?)
.Result("MNEM", "Initial", "Validated")
```

## Navigation inter-tables

GLIMS suit un modèle entité-relation. La navigation se fait par chaînage de méthodes :

```
Action → Order (dossier)
       → Object (patient)
       → Specimen (prélèvement)

Result → Action → Order
       → Specimen
       → Order (raccourci : .Result.Order)

Order  → Result("MNEM", statut_from, statut_to)
       → Specimen(n)
```

**Exemple de navigation depuis un contexte Result :**
```mispl
LOGICAL PROGRAM
  /* Accéder à l'âge du patient depuis un résultat */
  IF .Action().Object.AgeInYears(Today()) <= 19 THEN
    .Action().Order().AddRequest("B_COM_VR_PAL", ?, ?);
  ENDIF;
RETURN YES;
```

## Règle de distinction contexte Action vs Result

| Écriture | Contexte supposé |
|----------|-----------------|
| `Action.Order().AddRequest(...)` | Action |
| `.Action().Order().AddRequest(...)` | Result (le `.` = Result, puis `.Action()`) |
| `Result.Order.AddRequest(...)` | Result (accès direct Order sans Action) |
| `.Result.Order.AddRequest(...)` | Identique au précédent |

Les deux formes `.Action().Order()` et `Result.Order` aboutissent au même dossier dans la majorité des contextes résultat.
