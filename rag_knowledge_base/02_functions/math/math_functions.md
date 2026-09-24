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
Abs(-7)     /* retourne 7 */
Abs(0)      /* retourne 0 */
```

---

## Fabs
**Signature** : `Fractional Fabs(Fractional Entrée)`  
Valeur absolue d'un décimal. Utiliser `Fabs` pour les décimaux, `Abs` pour les entiers.

```mispl
Fabs(-0.25)     /* retourne 0.25 */
```

---

## Exp
**Signature** : `Fractional Exp(Fractional Base, Fractional Exposant)`  
Retour : `Base` élevé à l'exposant `Exposant` (Fractional).  
**Équivalent ABL** : `Base ** Exposant` (opérateur puissance)

```mispl
Exp(2, 10)     /* retourne 1024.0 */
Exp(4, 0.5)    /* retourne 2.0 */
Exp(5, -1)     /* retourne 0.2 */
```

---

## Fmod
**Signature** : `Fractional Fmod(Fractional Dividend, Fractional Divider)`  
Retour : reste de `Dividend / Divider` (Fractional).  
Entiers : opérateur `%`.

```mispl
Fmod(10.75, 2)   /* retourne 0.75 */
Fmod(12.0, 4)    /* retourne 0.0 */
/* Pour entiers : 17 % 5 retourne 2 */
```

---

## Log
**Signature** : `Fractional Log(Fractional Entrée)`  
Retour : ln(`Entrée`).

---

## Log10
**Signature** : `Fractional Log10(Fractional Entrée)`  
Retour : log10(`Entrée`).  
Utile pour les calculs de dilutions en bactériologie.

---

## Round
**Signature** : `Fractional Round(Fractional Valeur, Integer PositionsDécimales)`  
Arrondit `Valeur` au nombre de décimales spécifié.  
**Équivalent ABL** : `ROUND(x, n)`

```mispl
Round(7.849, 2)      /* retourne 7.85 */
Round(7.849, 0)      /* retourne 8.0 */
Round(7.849, 1)      /* retourne 7.8 */
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
Truncate(7.849, 2)      /* retourne 7.84 (pas 7.85) */
Truncate(7.849, 0)      /* retourne 7.0 */
```

**Différence Round/Truncate** :
- `Round(2.75, 1)` → `2.8`
- `Truncate(2.75, 1)` → `2.7`
