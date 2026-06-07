---
id: "functions_table_object_extended"
type: "fonction_core"
domaine: "table_object_extended"
langage_proxy: "Progress ABL / OpenEdge"
context: ["action", "result"]
table_abbrev: "obj"
return_type: "String | Logical | Result | Person | Diagnosis"
priority: "high"
keywords_fr: ["attribut objet", "résultat précédent", "antécédent", "historique patient", "propriété objet", "SetAttribute", "ClearAttribute", "GetResult", "résultat antérieur", "type objet déclaré", "pin patient", "données patient"]
anti_hallucination: ["ResultAttribute sur Object est une fonction de navigation différente de Result.Attribute"]
tags: [Object, obj, SetAttribute, ClearAttribute, GetResult, ResultAttribute, GetData, PatientData, PersonData, DeclaredType, PIN, AttributeList, GetDiagnosis, Result, Person]
---

# Fonctions étendues de la table Object

Complément de [object_functions.md](object_functions.md) — fonctions avancées non couvertes précédemment.

---

## SetAttribute / ClearAttribute / DeleteAttribute
**Signatures** :
```
Logical SetAttribute(Mnemonic AttributeMnemonic, Date StartDate)
Logical ClearAttribute(Mnemonic AttributeMnemonic, Date EndDate)
Logical DeleteAttribute(Mnemonic AttributeMnemonic, Date EndDate)
```
Définit, efface ou supprime un attribut personnalisé de l'objet à une date donnée.

```mispl
/* Marquer un attribut patient depuis un contexte Action */
Action.Object.SetAttribute("ALLERGIE_PENICILLINE", Today());
Action.Object.ClearAttribute("ALLERGIE_PENICILLINE", Today());
```

---

## GetResult
**Signature** : `Result GetResult(Mnemonic PropertyMnemonic, String ImposedResult, PositiveInteger Index, DateTime ReferenceTime)`  
Récupère un résultat de propriété (analyse) sur l'objet à une date de référence.

---

## ResultAttribute (sur Object)
**Signature** : `String ResultAttribute(String PropertyMnemonic, String ImposedResultValue, PositiveInteger Index, DateTime ReferenceTime, String AttributeName)`  
Lit un attribut d'un résultat de propriété sur l'objet. **Différent de `Result.Attribute`** — accès via l'objet plutôt que via un résultat courant.

---

## Result (sur Object)
**Signature** : `Result Result(Mnemonic PropertyMnemonic, PositiveInteger Index, DateTime ReferenceTime, ResultStatus MinimalStatus)`  
Retourne un résultat associé à l'objet (patient) par mnémonique de propriété.

---

## GetData / PatientData / PersonData
**Signatures** :
```
String GetData(String AttributeList)
String PatientData(String AttributeList)
String PersonData(String AttributeList)
```
Retournent des données formatées sur l'objet/patient selon une liste d'attributs.

---

## GetDiagnosis
**Signature** : `Diagnosis GetDiagnosis(Diagnosis Previous, String Code)`  
Itère sur les diagnostics associés à l'objet.

---

## DeclaredType
**Signature** : `ObjectType DeclaredType()`  
Retourne le type déclaré de l'objet (différent de `Action.ObjectType` qui est le type fonctionnel).

---

## PIN
**Signature** : `String PIN(String SourceMnemonic)`  
Retourne l'identifiant PIN de l'objet selon la source spécifiée.

---

## AttributeList
**Signature** : `String AttributeList(DateTime ReferenceTime, String FlagList, PositiveInteger MinimalSeverity, Logical FlagsOnly, Logical UseMnemonics, String Delimiter)`  
Retourne la liste formatée de tous les attributs de l'objet actifs à une date de référence.

---

## Person
**Signature** : `Person Person()`  
Retourne l'objet Person associé (si l'objet est un patient humain).

```mispl
/* Accéder aux données personne depuis un objet */
STRING nom;
nom := Action.Object.Person().LastName;
```

---

## MicrobiologicHistory
**Signature** : `String MicrobiologicHistory(Mnemonic SpecimenLayout, PositiveInteger MaximumDaysAgo, PositiveInteger SkipCount, PositiveInteger MaximumCount, String MaterialMnemonic, String ...)`  
Retourne l'historique microbiologique de l'objet sur une période.

---

## Age (variantes)
**Signatures** :
```
Fractional Age(Date ReferenceDate)       — âge en années (décimal)
Integer AgeInDays(Date ReferenceDate)    — âge en jours
Integer AgeInMonths(Date ReferenceDate)  — âge en mois
Fractional AgeInYears(Date ReferenceDate) — âge en années (décimal)
```

```mispl
/* Test pédiatrique complet */
INTEGER ageJ;
ageJ := Action.Object.AgeInDays(Today());
IF ageJ < 30 THEN /* nouveau-né */ ENDIF;
IF Action.Object.AgeInMonths(Today()) < 24 THEN /* nourrisson */ ENDIF;
```
