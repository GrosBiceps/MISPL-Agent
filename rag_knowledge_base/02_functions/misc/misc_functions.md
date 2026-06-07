---
id: "functions_misc"
type: "fonction_core"
domaine: "fonctions_diverses"
langage_proxy: "Progress ABL / OpenEdge"
context: ["all"]
table_abbrev: null
return_type: "String | Logical | Integer"
priority: "medium"
keywords_fr: ["utilisateur courant", "discipline", "rôle", "envoyer mail", "email", "imprimer", "post-traitement", "attribut site", "log", "journal", "séquence", "identifiant", "jour férié", "ferié", "OS serveur"]
anti_hallucination: []
tags: [CurrentUser, CurrentDepartment, CurrentRole, CurrentOS, PostProcess, SendMail, AddLogEntry, GetSiteAttribute, SetSiteAttribute, IsHoliday, NextValue, GetObjectId, GetCorrespondent, CurrentDevice, CurrentTerminal, Identifier, NumberToStringInFull, Expand]
---

# Fonctions diverses (indépendantes de table)

---

## CurrentUser
**Signature** : `String CurrentUser()`  
Retourne le nom de login de l'utilisateur GLIMS actif. Retourne `?` en contexte batch (broker/scheduler).

```mispl
IF CurrentUser() = "admin" THEN ...
```

---

## CurrentDepartment
**Signature** : `String CurrentDepartment()`  
Retourne le mnémonique de la discipline de l'utilisateur connecté.

---

## CurrentRole
**Signature** : `String CurrentRole()`  
Retourne le mnémonique du rôle sélectionné lors de la connexion.

---

## CurrentOS
**Signature** : `String CurrentOS()`  
Retourne `"UNIX"` ou `"WINDOWS"` selon la plateforme du serveur. Utile pour construire des chemins de fichiers.

---

## CurrentDevice / CurrentTerminal
**Signatures** :
```
String CurrentDevice()
String CurrentTerminal()
```
Retournent le nom du périphérique / terminal client. `?` en contexte batch.

---

## AddLogEntry
**Signature** : `Logical AddLogEntry(String TableName, PositiveInteger RecordId, String LogTypeName, LogSeverity LogSeverity, Logical NeedsChecking, String LogMessage)`  
Crée une entrée dans le journal d'audit GLIMS pour un enregistrement donné.  
`LogSeverity` : `"Info"`, `"Warning"`, `"Error"`.

---

## GetSiteAttribute / SetSiteAttribute
**Signatures** :
```
String GetSiteAttribute(String AttributeName)
String GetSiteAttribute(String SiteCode, AnyType Filter, String AttributeName)
Logical SetSiteAttribute(String AttributeName, String Value)
```
Lit/écrit un attribut de configuration globale du site GLIMS.  
La forme à 3 paramètres permet de lire un attribut spécifique à un site nommé avec filtre.

```mispl
/* Forme simple */
STRING val;
val := GetSiteAttribute("NomParametre");

/* Forme avancée avec site spécifique — utilisée en production CHU */
STRING responsable;
responsable := GetSiteAttribute("SpecificSite", ?, "B_Biologiste");
/* Lit l'attribut B_Biologiste du site SpecificSite */
```

---

## GetObjectId
**Signature** : `PositiveInteger GetObjectId(String ObjectMnemonic)`  
Retourne l'ID interne d'un objet (patient/device) par son mnémonique.

---

## GetCorrespondent / GetCorrespondentId
**Signatures** :
```
Correspondent GetCorrespondent(String Mnemonic)
PositiveInteger GetCorrespondentId(String Mnemonic)
```
Résout un correspondant (médecin/service prescripteur) par son mnémonique.

---

## Identifier
**Signature** : `String Identifier(String TableName, PositiveInteger RecordId, String IdentifierType)`  
Retourne un identifiant formaté pour un enregistrement. Utile pour les étiquettes et exports.

```mispl
/* Obtenir l'IPP formaté d'un objet patient */
STRING ipp;
ipp := Identifier("Object", Action.Object.Id, "IPP");
```

---

## IsHoliday
**Signature** : `Logical IsHoliday(Date Date)`  
Retourne YES si la date est un jour férié configuré dans GLIMS.

```mispl
/* Tester si aujourd'hui est férié (contexte garde) */
IF IsHoliday(Today()) THEN
  /* Traitement de garde jour férié */
  Result.Order.AddRequest("B_REVUE_FERIE", ?, ?);
ENDIF;
```

---

## NextValue
**Signature** : `Integer NextValue(String SequenceName)`  
Incrément atomique d'un compteur nommé (séquence GLIMS). Génère des numéros séquentiels uniques.

```mispl
/* Générer un numéro de lot unique */
INTEGER numLot;
numLot := NextValue("LOT_SEQUENCE");
STRING libLot;
libLot := IntegerToString(numLot, "%06d");   /* ex: "000042" */
```

---

## NumberToStringInFull
**Signature** : `String NumberToStringInFull(Fractional Number, String Language)`  
Retourne le nombre en toutes lettres dans la langue spécifiée (ex: `"fr"` → `"quarante-deux"`).

---

## SendMail
**Signature** : `Logical SendMail(String SiteMnemonic, String Subject, String Body, MailPriority Priority)`  
Envoie un e-mail via la configuration messagerie du site GLIMS.

**Accès contextuel depuis un objet Issuer** :
```mispl
.Issuer.SendMail("SITE", "Sujet alerte", "Corps du message", MailPriority["High"]);
```

---

## Expand
**Signature** : `String Expand(String TableName, PositiveInteger RecordId, String OriginalText, String ParameterList)`  
Évalue un texte dynamique GLIMS dans le contexte d'un enregistrement donné.  
`ParameterList` format : `"Tag=Valeur\Tag2=Valeur2"`.

---

## GetCode
**Signature** : `String GetCode(String TableName, PositiveInteger RecordId)`  
Retourne le code/mnémonique d'un enregistrement identifié par sa table et son ID interne.

---

## DatedIdentifier
**Signature** : `String DatedIdentifier(String Prefix, Date Date, Integer Length)`  
Génère un identifiant horodaté de la forme `Prefix + YYYYMMDD + séquence`.
