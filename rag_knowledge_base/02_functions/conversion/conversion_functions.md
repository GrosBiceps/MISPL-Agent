---
id: "functions_conversion"
type: "fonction_core"
domaine: "conversion_types"
langage_proxy: "Progress ABL / OpenEdge"
context: ["all"]
table_abbrev: null
return_type: "String | Integer | Fractional | Enumerated"
priority: "critical"
keywords_fr: ["convertir", "conversion", "type", "entier vers chaîne", "décimal vers chaîne", "chaîne vers entier", "chaîne vers décimal", "énuméré vers texte", "type objet", "ObjectType", "délai en minutes", "valeur numérique depuis texte"]
anti_hallucination: ["StringToReal n'existe pas → StringToFractional", "Val n'existe pas → StringToFractional", "CInt n'existe pas → StringToInteger", "CStr n'existe pas → ToString ou FractionalToString"]
tags: [conversion, StringToFractional, StringToInteger, EnumeratedToString, IntegerToString, FractionalToString, FractionalToInteger, ToString, StringToEnumerated, ObjectType, person, animal]
---

# Fonctions de conversion de types de données

Équivalent ABL : conversions implicites et fonctions `INTEGER()`, `DECIMAL()`, `STRING()`, `LOGICAL()`.

---

## EnumeratedToString
**Signature** : `String EnumeratedToString(String EnumeratorClassName, Enumerated Value)`  
Convertit une valeur d'un type énuméré GLIMS en sa représentation textuelle.  
**Cas d'usage clé** : lire `ObjectType` d'une Action pour distinguer patient humain d'un animal ou d'un device.

```mispl
/* Vérifier que l'objet est bien un patient humain */
STRING ObjectType;
ObjectType := EnumeratedToString("ObjectType", Action.ObjectType);
IF ObjectType = "person" THEN
  /* traitement spécifique patient */
ENDIF;
```

**Valeurs courantes pour ObjectType** : `"person"`, `"animal"`, `"device"`, `"group"`

---

## FractionalToInteger
**Signature** : `Integer FractionalToInteger(Fractional Fractional)`  
Convertit un décimal en entier par **troncature** (pas d'arrondi).  
**Équivalent ABL** : `TRUNCATE(x, 0)` ou cast implicite.

```mispl
INTEGER entier;
entier := FractionalToInteger(5.9);   /* retourne 5, pas 6 */
```

---

## FractionalToString
**Signature** : `String FractionalToString(Fractional Fractional, String Format)`  
Convertit un décimal en chaîne selon une directive de format style `printf` :

| Directive | Description |
|-----------|-------------|
| `%f` | Notation décimale standard (6 décimales par défaut) |
| `%E` | Notation scientifique `m.nnnnnE±xx` |
| `%G` | Le plus court entre `%E` et `%f` |
| `%7.2f` | Largeur 7, 2 décimales |

```mispl
FractionalToString(40.3399, "%7.2f")   /* "  40.34" */
FractionalToString(40.3399, "%G")       /* "40.3399" */
```

---

## IntegerToString
**Signature** : `String IntegerToString(Integer Integer, String Format)`  
Convertit un entier en chaîne selon directive `printf` : `%d` (décimal), `%o` (octal), `%x` (hexadécimal).

```mispl
IntegerToString(255, "%d")    /* "255" */
IntegerToString(255, "%x")    /* "ff" */
IntegerToString(42, "%05d")   /* "00042" */
```

---

## StringToEnumerated
**Signature** : `Enumerated StringToEnumerated(String EnumeratorClassName, String String)`  
Inverse de `EnumeratedToString` — convertit une chaîne en valeur d'un type énuméré GLIMS.  
Utile pour assigner une valeur d'énumération depuis une variable texte.

```mispl
/* Convertir une chaîne vers un type énuméré GLIMS */
/* Exemple : assigner ObjectType depuis une variable */
STRING typeStr;
typeStr := "person";
/* Utilisation dans une comparaison — généralement EnumeratedToString est plus courant */
IF EnumeratedToString("ObjectType", Action.ObjectType) = typeStr THEN ...
```

---

## StringToFractional
**Signature** : `Fractional StringToFractional(String)`  
Convertit une chaîne de caractères en décimal. Retourne `?` si la chaîne n'est pas un nombre valide.  
**ATTENTION** : Nom exact `StringToFractional`, **pas** `StringToReal`, `Val()`, ou `CDbl()`.  
**Équivalent ABL** : `DECIMAL(s)`

```mispl
/* Vérifier qu'un résultat lié a bien une valeur numérique */
LOGICAL PROGRAM
  IF StringToFractional(.Result.RelatedResult("B_VOLUME_UR").Attribute("Value")) <> ?
    AND StringToFractional(.Result.RelatedResult("B_TEMPS_RECUEIL").Attribute("Value")) <> ?
  THEN
    Action.Order().AddRequest("B_CALC_CREAT_UR", ?, ?);
  ENDIF;
RETURN YES;
```

---

## StringToInteger
**Signature** : `Integer StringToInteger(String)`  
Convertit une chaîne en entier. Retourne `?` si conversion impossible.  
**ATTENTION** : Nom exact `StringToInteger`, **pas** `CInt()`, `Int()`, ou `Val()`.  
**Équivalent ABL** : `INTEGER(s)`

```mispl
/* Calculer un délai en minutes et déclencher si >= 240 min (4h) */
LOGICAL PROGRAM
  IF StringToInteger(.Result.Attribute("Value")) >= (4 * 60)
    AND .Action().Order().Result("B_COB_LACT_SG", ?, ?).Id <> ?
  THEN
    .SetManualSeverity(3);
    Action.Order().AddRequest("B_COMM_DELAI_SUP4H", ?, ?);
  ENDIF;
RETURN YES;
```

---

## ToString
**Signature** : `String ToString(AnyType Value)`  
Convertit n'importe quel type en sa représentation chaîne par défaut.  
Moins de contrôle sur le format que `FractionalToString` ou `IntegerToString` — préférer ceux-ci quand le format compte.

```mispl
/* Conversion générique — quand le format exact n'importe pas */
STRING s;
s := ToString(42);           /* "42" */
s := ToString(3.14);         /* "3.14" (format système) */
s := ToString(Today());      /* représentation date système */
```
