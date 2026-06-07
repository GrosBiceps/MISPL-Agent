---
id: "functions_table_action"
type: "fonction_core"
domaine: "table_action"
langage_proxy: "Progress ABL / OpenEdge"
context: ["action"]
table_abbrev: "actn"
return_type: "Order | Object | Specimen | Result | Enumerated"
priority: "critical"
keywords_fr: ["type objet", "patient humain", "vérifier si patient", "personne", "âge patient", "accéder dossier depuis action", "objet associé", "prélèvement associé", "résultat courant depuis action"]
anti_hallucination: ["ObjectType doit être converti avec EnumeratedToString avant comparaison string"]
tags: [Action, actn, ObjectType, Order, Object, Specimen, EnumeratedToString, person, animal, AgeInYears, Result]
---

# Fonctions de la table Action

Table GLIMS : `actn` — représente une unité de travail analytique (une analyse demandée sur un prélèvement).  
Dans un contexte MISPL Action, `Action` (sans point) désigne l'Action courante.

---

## Order (navigation)
**Signature** : `Order Order()`  
Accède au dossier (Order) associé à l'Action.

```mispl
Action.Order().AddRequest("MNEM", ?, ?);
Action.Order().PostProcess(YES, YES, YES, YES, YES, NO, YES);
```

---

## ObjectType (champ énuméré)
**Type** : `Enumerated (ObjectType)`  
Type de l'objet (patient) associé à l'Action.  
Valeurs courantes : `"person"`, `"animal"`, `"device"`, `"group"`.  
**Toujours convertir avec `EnumeratedToString`** avant de comparer à une chaîne.

```mispl
STRING objType;
objType := EnumeratedToString("ObjectType", Action.ObjectType);
IF objType = "person" THEN
  /* traitement pour patient humain uniquement */
ENDIF;
```

---

## Object (navigation)
**Accès** : `Action.Object`  
Accède à l'objet (patient, animal, device) associé à l'Action.  
Méthodes disponibles depuis Object : `AgeInYears()`, `BirthDate`, `Sex`, `LastName`, `FirstName`.

```mispl
/* Âge du patient au moment de l'analyse */
INTEGER age;
age := FractionalToInteger(Action.Object.AgeInYears(Today()));
```

---

## AgeInYears (méthode de Object)
**Signature** : `Fractional AgeInYears(Date ReferenceDate)`  
Retourne l'âge de l'objet en années à la date de référence.  
**Point d'accès** : `Action.Object.AgeInYears(Today())` depuis contexte Action,  
ou `.Action().Object.AgeInYears(Today())` depuis contexte Result.

```mispl
IF Action.Object.AgeInYears(Today()) <= 19 THEN
  Action.Order().AddRequest("B_COM_VR_PAL", ?, ?);
ENDIF;
```

---

## Specimen (navigation)
**Accès** : `Action.Specimen`  
Accède au prélèvement associé à l'Action.

```mispl
/* Lire un attribut du prélèvement depuis l'action */
STRING material;
material := Action.Specimen.Attribute("Material");
```

---

## Cancel
**Signature** : `Logical Cancel(String Reason, String Comment)`  
Annule l'action courante avec un code raison et un commentaire.

```mispl
Action.Cancel("Discontinue", "Analyse non pertinente");
```

---

## Attribute
**Signature** : `String Attribute(String AttributeName)`  
Lit un attribut personnalisé de l'Action.

---

## InputResult / OutputResult
**Signatures** :
```
Result InputResult(Mnemonic ResultMnemonic)
Result OutputResult(Mnemonic ResultMnemonic)
```
Accèdent aux résultats d'entrée/sortie de l'action (contexte analyseur/worklist).

---

## InputByMnemonic
**Signature** : `Logical InputByMnemonic(String Mnemonic, String Value)`  
Saisit un résultat sur l'action par son mnémonique depuis MISPL.

---

## PropertyList
**Signature** : `String PropertyList(...)`  
Retourne la liste des propriétés disponibles sur l'action.

---

## ResultOperation
**Signature** : `Logical ResultOperation(String Operation, String Parameters)`  
Exécute une opération sur les résultats de l'action.

---

## Result (navigation depuis Action)
**Accès** : `.Result` (dans contexte Action, le `.` initial désigne l'Action)  
Accède au Result associé à l'Action courante.

```mispl
/* Depuis contexte Action, accéder au résultat courant */
IF .Result.Mantissa <> ? THEN
  Action.Order().AddRequest("B_COMM_AMH", ?, ?);
ENDIF;
```

---

## Cas d'usage CHU — Vérification ObjectType avant AddRequest

```mispl
/* B_Ajout B_ALZ_VR_RATIO : ne déclencher que pour patients humains */
LOGICAL PROGRAM
  STRING ObjectType;
  ObjectType := EnumeratedToString("ObjectType", Action.ObjectType);
  IF ObjectType = "person" THEN
    IF .Result.Mantissa <> ? THEN
      Action.Order().AddRequest("B_ALZ_VR_RATIO", ?, ?);
    ENDIF;
    RETURN YES;
  ELSE
    RETURN NO;
  ENDIF;
```

**Pattern récurrent** : de nombreux scripts CHU vérifient `ObjectType = "person"` avant d'agir sur un dossier, pour exclure les analyses vétérinaires ou sur devices.
