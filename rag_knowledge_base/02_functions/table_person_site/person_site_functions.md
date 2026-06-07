---
id: "functions_table_person_site"
type: "fonction_core"
domaine: "table_person_site"
langage_proxy: "Progress ABL / OpenEdge"
context: ["all"]
table_abbrev: ["prsn", "gsit", "ssit", "usr", "role"]
return_type: "String | Logical | Person | Encounter | Stay"
priority: "medium"
keywords_fr: ["personne patient", "hospitalisation", "séjour", "numéro national", "groupe sanguin", "antécédents", "historique patient", "site GLIMS", "utilisateur", "privilège", "rôle utilisateur", "base de test", "SendMail utilisateur", "SendMail rôle"]
anti_hallucination: ["sc_User.SendMail prend 3 paramètres (pas de From)", "sc_Role.SendMail envoie à tous les utilisateurs du rôle"]
tags: [Person, prsn, gp_Site, gsit, SpecificSite, ssit, sc_User, usr, sc_Role, role, Hospitalized, Stay, Encounter, CheckNationalNumber, ExtendedBirthDate, SendMail, HasPrivilege, IsTestDatabase, CurrentSessionHasPrivilege, GetUser, GetRole]
---

# Fonctions des tables Person, Site, User, Role

---

## Person (prsn) — fonctions clés pour la biologie médicale

### ExtendedBirthDate
**Signature** : `String ExtendedBirthDate(String Format)`  
Retourne la date de naissance formatée selon le format spécifié.

### CheckNationalNumber
**Signature** : `String CheckNationalNumber(String Matriculation, Integer MatriculationType)`  
Valide un numéro national (NISS belge, etc.) et retourne un message d'erreur ou chaîne vide si valide.

### Hospitalized
**Signature** : `Logical Hospitalized(DateTime TargetTime)`  
Teste si le patient est hospitalisé à un instant donné.

### Stay / Encounter
```
Stay Stay(DateTime TargetTime)
Encounter Encounter(Institution Institution, DateTime EncounterTime)
```
Accèdent aux données d'hospitalisation/séjour du patient.

### GetEncounter
**Signature** : `Encounter GetEncounter(Mnemonic Institution, Mnemonic Type, ResidenceType ResidenceType, DateTime ReferenceTime, Integer HistoryIndex)`  
Recherche un épisode de soin selon critères.

### SetAntigen / GetAntigen
```
Logical SetAntigen(String AntigenMnemonic, Logical Presence)
Logical GetAntigen(String AntigenMnemonic)
```
Définit/lit la présence d'un antigène érythrocytaire (groupe sanguin).

---

## gp_Site (gsit) — fonctions globales de site

Ces fonctions sont accessibles depuis n'importe quel contexte MISPL.

### IsTestDatabase
**Signature** : `Logical IsTestDatabase()`  
Retourne YES si l'environnement courant est une base de données de test.

```mispl
/* Désactiver les envois d'email en mode test */
IF NOT IsTestDatabase() THEN
  .Correspondent.SendMail("SITE", "Sujet", "Corps", MailPriority["Normal"]);
ENDIF;
```

### CurrentSessionHasPrivilege
**Signature** : `Logical CurrentSessionHasPrivilege(String Privilege)`  
Teste si la session courante possède un privilège GLIMS nommé.

### GetRole
**Signature** : `sc_Role GetRole(Mnemonic Mnemonic)`  
Retourne un objet rôle par son mnémonique.

### GetUser
**Signature** : `sc_User GetUser(String LoginName)`  
Retourne un objet utilisateur par son nom de connexion.

### FindCommandByTableAndDescription
**Signature** : `bt_Command FindCommandByTableAndDescription(String TableName, String CommandDescription)`  
Recherche une commande GLIMS par table et description.

### GetAttachments
**Signature** : `String GetAttachments(Mnemonic TableName, Recid RecordId, String CategoryName)`  
Retourne la liste des pièces jointes d'un enregistrement.

---

## sc_User (usr)

### HasPrivilege
**Signature** : `Logical HasPrivilege(String Privilege)`  
Teste si cet utilisateur possède un privilège.

```mispl
/* Vérifier si l'utilisateur peut valider */
sc_User user;
user := GetUser(CurrentUser());
IF user.HasPrivilege("VALIDATE_RESULT") THEN
  .Validate();
ENDIF;
```

### SendMail (User)
**Signature** : `Logical SendMail(String Subject, String Content, MailPriority Priority)`  
Envoie un message à cet utilisateur (interne ou externe selon sa préférence).  
**Pas de paramètre `From`** — l'expéditeur est l'utilisateur courant.

```mispl
/* Notifier le biologiste responsable */
sc_User bio;
bio := GetUser("martin");
bio.SendMail("Valeur critique PSA", "Patient DUPONT — PSA = 12 ng/mL", MailPriority["High"]);
```

---

## sc_Role (role)

### SendMail (Role)
**Signature** : `Logical SendMail(String Subject, String Content, MailPriority Priority)`  
Envoie un message à TOUS les utilisateurs ayant ce rôle.  
Utile pour les alertes à l'équipe de garde.

```mispl
/* Alerter tous les biologistes de garde */
sc_Role garde;
garde := GetRole("BIOLOGISTE_GARDE");
garde.SendMail("Panne analyseur", "L'analyseur B_COBAS est hors service", MailPriority["High"]);
```
