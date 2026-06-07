---
id: "functions_table_object"
type: "fonction_core"
domaine: "table_object"
langage_proxy: "Progress ABL / OpenEdge"
context: ["action", "result"]
table_abbrev: "obj"
return_type: "Fractional | Date | Enumerated | String"
priority: "high"
keywords_fr: ["âge du patient", "date naissance", "sexe", "nom patient", "prénom", "mineur", "pédiatrique", "patient", "objet", "calcul âge"]
anti_hallucination: []
tags: [Object, obj, AgeInYears, BirthDate, Sex, LastName, FirstName, Attribute, Action.Object, pediatrique]
---

# Fonctions de la table Object (Patient/Objet)

Table GLIMS : `obj` — représente l'entité sur laquelle porte l'analyse (patient humain, animal, device, groupe).  
Accès : `Action.Object` depuis contexte Action, ou `.Action().Object` depuis contexte Result.

---

## AgeInYears
**Signature** : `Fractional AgeInYears(Date ReferenceDate)`  
Calcule l'âge de l'objet en années à la date spécifiée.  
Tient compte des années bissextiles. Résultat décimal (ex: `19.7`).  
Utiliser `FractionalToInteger()` pour obtenir un entier.

```mispl
/* Conditionner selon l'âge du patient */
IF Action.Object.AgeInYears(Today()) <= 19 THEN
  Action.Order().AddRequest("B_COM_VR_PAL", ?, ?);
ENDIF;
```

---

## BirthDate (champ)
**Type** : `Date`  
Date de naissance de l'objet.

```mispl
DATE naissance;
naissance := Action.Object.BirthDate;
```

---

## Sex (champ énuméré)
**Type** : `Enumerated (Sex)`  
Sexe de l'objet. Convertir : `EnumeratedToString("Sex", Action.Object.Sex)`.  
Valeurs courantes : `"male"`, `"female"`, `"unknown"`.

---

## LastName / FirstName (champs)
**Types** : `String`  
Nom et prénom de l'objet.

---

## Attribute
**Signature** : `String Attribute(String AttributeName)`  
Lit un attribut personnalisé défini sur l'objet.

---

## ObjectType (champ énuméré — hérité de Action)
**Note** : `ObjectType` est accessible via `Action.ObjectType`, pas directement via `Action.Object.ObjectType`.  
Voir `table_action/action_functions.md` pour le pattern de vérification.

---

## Cas d'usage CHU — Vérification âge pour bornes PAL pédiatriques

```mispl
/* B_Ajout B_COM_VR_PAL si <= 19 ans : les valeurs de référence pédiatriques diffèrent */
LOGICAL PROGRAM
  IF Action.Object.AgeInYears(Today()) <= 19
    AND .Result.Mantissa <> ?
    AND NOT (Substr(.Result.Attribute("Value"), 1, 1) = "<")
    AND NOT (Substr(.Result.Attribute("Value"), 1, 1) = ">")
  THEN
    Action.Order().AddRequest("B_COM_VR_PAL", ?, ?);
  ENDIF;
RETURN YES;
```
