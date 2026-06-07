---
id: "functions_shared_variables"
type: "fonction_core"
domaine: "variables_partagees"
langage_proxy: "Progress ABL / OpenEdge"
context: ["all"]
table_abbrev: null
return_type: "Date | Fractional | Integer | Logical | String | Void"
priority: "low"
keywords_fr: ["variable partagée", "variable globale", "lire variable", "écrire variable", "partager entre scripts", "Peek", "Poke", "mémoire partagée", "PeekCharacter", "PokeCharacter", "lire chaine partagée", "écrire chaine partagée", "variable string partagée", "biologiste responsable variable", "variable garde"]
anti_hallucination: ["PeekCharacter est le nom correct — PAS PeekString", "PokeCharacter est le nom correct — PAS PokeString"]
warning: "Ces fonctions ne sont pas destinées à la configuration standard. Usage uniquement sur instruction explicite de l'éditeur GLIMS."
tags: [PeekDate, PeekDecimal, PeekInteger, PeekLogical, PeekRecId, PeekCharacter, PokeDate, PokeDecimal, PokeInteger, PokeLogical, PokeRecId, PokeCharacter, shared_variables, peek, poke, variable_partagee]
---

# Fonctions de variables partagées (Peek/Poke)

**Usage restreint** : Ces fonctions permettent l'accès à des variables partagées en mémoire entre sessions GLIMS. Réservées aux usages avancés sur instruction de l'éditeur du logiciel.

---

## PeekCharacter
**Signature** : `String PeekCharacter(String SharedCharVar)`  
Lit la valeur d'une variable de chaîne partagée entre scripts MISPL.  
**Nom exact : `PeekCharacter` — pas `PeekString`** (PeekString n'existe pas).

```mispl
/* Lire le biologiste de garde stocké dans une variable partagée */
STRING biologiste;
biologiste := PeekCharacter("B_Biologiste");
IF biologiste <> ? THEN
  .AddInternalComment("Biologiste garde: " + biologiste, YES);
ENDIF;
```

---

## PeekInteger / PeekDecimal / PeekDate / PeekLogical / PeekRecId
**Signatures** :
```
Integer   PeekInteger(String SharedIntegerVariable)
Fractional PeekDecimal(String SharedDecimalVariableName)
Date      PeekDate(String SharedDateVariableName)
Logical   PeekLogical(String SharedLogicalVariableName)
Recid     PeekRecId(String SharedRecidVariableName)
```
Lisent des variables partagées selon leur type.

```mispl
INTEGER compteur;
compteur := PeekInteger("B_COMPTEUR_NC");

DATE dateRef;
dateRef := PeekDate("B_DATE_GARDE");
```

---

## PokeCharacter
**Signature** : `Void PokeCharacter(String SharedStringVariable, String Value)`  
Écrit une valeur dans une variable de chaîne partagée.  
**Nom exact : `PokeCharacter` — pas `PokeString`** (PokeString n'existe pas).

```mispl
/* Stocker le biologiste responsable de garde */
PokeCharacter("B_Biologiste", "martin");

/* Lire depuis un autre script */
STRING bio;
bio := PeekCharacter("B_Biologiste");   /* retourne "martin" */
```

---

## PokeInteger / PokeDecimal / PokeDate / PokeLogical / PokeRecId
**Signatures** :
```
Void PokeInteger(String SharedIntegerVariableName, Integer Value)
Void PokeDecimal(String SharedDecimalVariableName, Fractional Value)
Void PokeDate(String SharedDateVariableName, Date Value)
Void PokeLogical(String SharedLogicalVariableName, Logical Value)
Void PokeRecId(String SharedRecidVariableName, Recid Value)
```
Écrivent des variables partagées selon leur type.

```mispl
PokeInteger("B_COMPTEUR_NC", PeekInteger("B_COMPTEUR_NC") + 1);
PokeDate("B_DATE_GARDE", Today());
```
