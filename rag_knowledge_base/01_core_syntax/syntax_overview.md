---
id: "syntax_programme_structure"
type: "syntaxe_core"
domaine: "structure_programme"
langage_proxy: "Progress ABL / OpenEdge"
context: ["all"]
table_abbrev: null
return_type: null
priority: "critical"
keywords_fr: ["programme", "déclarer", "type", "retour", "variable", "instruction", "opérateur", "division", "entier", "inconnu", "NULL", "LOGICAL PROGRAM", "INTEGER PROGRAM", "CHARACTER PROGRAM"]
anti_hallucination: ["FRACTIONAL PROGRAM n'existe pas — utiliser DECIMAL PROGRAM ou LOGICAL PROGRAM"]
tags: [programme, structure, types, retour, declaration, LOGICAL, INTEGER, CHARACTER, DECIMAL, DATE, PROGRAM, RETURN, IF, WHILE, REPEAT]
---

# Structure d'un programme MISPL

## Analogie Progress ABL
En ABL, un bloc de code est encapsulé dans `PROCEDURE ... END PROCEDURE` avec des déclarations de variables et un flux de contrôle explicite. MISPL suit la même philosophie : un programme est une unité compilable avec un type de retour déclaré, des variables locales, des instructions, et une valeur de retour obligatoire.

## Signature technique

```
(CHARACTER | DATE | DECIMAL | INTEGER | LOGICAL) PROGRAM
  { <Déclaration> }
  { <Instruction> }
RETURN <Expression>;
```

## Types de programmes disponibles

| Type déclaré | Valeur retournée |
|--------------|-----------------|
| `LOGICAL PROGRAM` | YES / NO |
| `CHARACTER PROGRAM` | Chaîne de texte |
| `INTEGER PROGRAM` | Entier |
| `DECIMAL PROGRAM` | Décimal (FRACTIONAL) |
| `DATE PROGRAM` | Date |

## Déclaration de variables

```mispl
LOGICAL PROGRAM
  STRING maVariable;
  INTEGER compteur;
  FRACTIONAL ratio;
  DATE dateRef;
  ...
RETURN YES;
```

**Types disponibles** : DATE, DATETIME, FRACTIONAL, INTEGER, LOGICAL, STRING, TIME, ou une Classe/Enumération GLIMS.

## Instructions disponibles

| Type | Syntaxe |
|------|---------|
| Conditionnel | `IF <expr> THEN ... [ELSE ...] ENDIF;` |
| Boucle WHILE | `WHILE <expr> DO ... DONE;` |
| Boucle REPEAT | `REPEAT ... UNTIL <expr>;` |
| Assignation | `variable := <expression>;` |
| Appel de méthode | `<objet>.<Methode>(<params>);` |

## Opérateurs

```
Arithmétique : + - * / %
Relationnel   : < <= > >= = <>  (ou LT LE GT GE EQ NE)
Logique       : AND OR NOT  (ou && || !)
```

**Attention division entière** : `321 / 60` retourne `5` (troncature).  
Pour un résultat décimal, forcer : `321.0 / 60` retourne `5.35`.

## Valeur inconnue

Le symbole `?` représente la valeur inconnue (NULL ABL).  
Tester : `IF maVar <> ? THEN ...`  
Passer en paramètre optionnel : `AddRequest("MNEM", ?, ?)`

## Exemple minimal

```mispl
LOGICAL PROGRAM
  IF .NumericValue() <> ? AND .NumericValue() >= 3.5 THEN
    .Action().Order().AddRequest("PSAL", ?, YES);
    .MarkAsSolicited();
  ENDIF;
RETURN YES;
```
