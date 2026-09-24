---
id: "syntax_programme_structure"
type: "syntaxe_core"
domaine: "structure_programme"
langage_proxy: "Progress ABL / OpenEdge"
context: ["all"]
table_abbrev: null
return_type: null
priority: "critical"
keywords_fr: ["programme", "déclarer", "type", "retour", "variable", "instruction", "opérateur", "division", "entier", "inconnu", "NULL", "type de retour"]
anti_hallucination: ["Ne jamais écrire de ligne d'en-tête <TYPE> PROGRAM : inutile dans GLIMS, le type de retour est défini dans la configuration du programme"]
tags: [programme, structure, types, retour, declaration, LOGICAL, INTEGER, CHARACTER, DECIMAL, DATE, PROGRAM, RETURN, IF, WHILE, REPEAT]
---

# Structure d'un programme MISPL

## Analogie Progress ABL
En ABL, un bloc de code est encapsulé dans `PROCEDURE ... END PROCEDURE` avec des déclarations de variables et un flux de contrôle explicite. MISPL suit la même philosophie : un programme est une unité compilable dont le type de retour est défini dans la configuration GLIMS (aucune ligne d'en-tête à écrire), des variables locales, des instructions, et une valeur de retour obligatoire.

## Signature technique

```
{ <Déclaration> }
{ <Instruction> }
RETURN <Expression>;
```

## Types de programmes disponibles

| Type de retour (défini dans la configuration GLIMS du programme) | Valeur retournée |
|--------------|-----------------|
| `LOGICAL` | YES / NO |
| `CHARACTER` | Chaîne de texte |
| `INTEGER` | Entier |
| `DECIMAL` | Décimal (FRACTIONAL) |
| `DATE` | Date |

## Déclaration de variables

```mispl
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

**Attention division entière** : `7 / 2` retourne `3` (troncature).  
Pour un résultat décimal, forcer : `7.0 / 2` retourne `3.5`.

## Valeur inconnue

Le symbole `?` représente la valeur inconnue (NULL ABL).  
Tester : `IF maVar <> ? THEN ...`  
Passer en paramètre optionnel : `AddRequest("MNEM", ?, ?)`

## Exemple minimal

```mispl
  IF .NumericValue() <> ? AND .NumericValue() >= 3.5 THEN
    .Action().Order().AddRequest("PSAL", ?, YES);
    .MarkAsSolicited();
  ENDIF;
RETURN YES;
```
