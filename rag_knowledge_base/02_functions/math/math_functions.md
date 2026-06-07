---
id: "functions_math"
type: "fonction_core"
domaine: "calculs_mathematiques"
langage_proxy: "Progress ABL / OpenEdge"
context: ["all"]
table_abbrev: null
return_type: "Integer | Fractional"
priority: "medium"
keywords_fr: ["valeur absolue", "arrondir", "racine carrée", "logarithme", "puissance", "modulo", "tronquer", "exponentielle", "calcul", "arrondi"]
anti_hallucination: ["Round arrondit au nombre de décimales spécifié — pas Round() sans paramètre"]
tags: [Abs, Fabs, Exp, Fmod, Log, Log10, Round, Sqrt, Truncate, math, calcul, arrondi, modulo, logarithme]
---

# Fonctions mathématiques

Équivalent ABL : `ABS()`, `EXP()`, `LOG()`, `ROUND()`, `SQRT()`, `TRUNCATE()`.

---

## Abs
**Signature** : `Integer Abs(Integer Entrée)`  
Valeur absolue d'un entier.  
**Équivalent ABL** : `ABS(n)`

```mispl
Abs(-23)    /* retourne 23 */
Abs(23)     /* retourne 23 */
```

---

## Fabs
**Signature** : `Fractional Fabs(Fractional Entrée)`  
Valeur absolue d'un décimal. Utiliser `Fabs` pour les décimaux, `Abs` pour les entiers.

```mispl
Fabs(-14.56)    /* retourne 14.56 */
```

---

## Exp
**Signature** : `Fractional Exp(Fractional Base, Fractional Exposant)`  
Élève `Base` à la puissance `Exposant`.  
**Équivalent ABL** : `Base ** Exposant` (opérateur puissance)

```mispl
Exp(10, 2)     /* retourne 100.0 */
Exp(10, -2)    /* retourne 0.01 */
Exp(2.7, 2)    /* retourne 7.29 */
```

---

## Fmod
**Signature** : `Fractional Fmod(Fractional Dividend, Fractional Divider)`  
Reste de la division décimale `Dividend / Divider`.  
Pour des entiers, utiliser l'opérateur `%` directement.

```mispl
Fmod(83.5, 8)    /* retourne 3.5 */
Fmod(88.0, 8)    /* retourne 0.0 */
/* Pour entiers : 83 % 8 retourne 3 */
```

---

## Log
**Signature** : `Fractional Log(Fractional Entrée)`  
Logarithme naturel (base e) de `Entrée`.

---

## Log10
**Signature** : `Fractional Log10(Fractional Entrée)`  
Logarithme décimal (base 10) de `Entrée`.  
Utile pour les calculs de dilutions en bactériologie.

---

## Round
**Signature** : `Fractional Round(Fractional Valeur, Integer PositionsDécimales)`  
Arrondit `Valeur` au nombre de décimales spécifié.  
**Équivalent ABL** : `ROUND(x, n)`

```mispl
Round(123.456, 2)    /* retourne 123.46 */
Round(123.456, 0)    /* retourne 123.0 */
Round(123.456, 1)    /* retourne 123.5 */
```

**Usage biochimie** : arrondir un ratio calculé avant comparaison à un seuil.

---

## Sqrt
**Signature** : `Fractional Sqrt(Fractional Entrée)`  
Racine carrée de `Entrée`.  
**Équivalent ABL** : `SQRT(x)`

```mispl
Sqrt(9.0)      /* retourne 3.0 */
Sqrt(144.0)    /* retourne 12.0 */
```

---

## Truncate
**Signature** : `Fractional Truncate(Fractional Valeur, Integer PositionsDécimales)`  
Tronque `Valeur` au nombre de décimales spécifié (pas d'arrondi).  
**Équivalent ABL** : `TRUNCATE(x, n)`

```mispl
Truncate(123.456, 2)    /* retourne 123.45 (pas 123.46) */
Truncate(123.456, 0)    /* retourne 123.0 */
```

**Différence Round/Truncate** :
- `Round(2.75, 1)` → `2.8`
- `Truncate(2.75, 1)` → `2.7`
