---
id: "functions_table_correspondent"
type: "fonction_core"
domaine: "table_correspondent"
langage_proxy: "Progress ABL / OpenEdge"
context: ["all"]
table_abbrev: "crsp"
return_type: "String | Logical | Correspondent | Person | Fund | Bank | Firm"
priority: "high"
keywords_fr: ["correspondant", "médecin prescripteur", "envoyer email à médecin", "identification patient", "numéro national", "envoi résultats", "destinataire", "accord financier", "code RIZIV", "groupe correspondant", "SendMail correspondant"]
anti_hallucination: ["Correspondent.SendMail prend 4 paramètres : From, Subject, Content, Priority"]
tags: [Correspondent, crsp, SendMail, Attribute, Person, Fund, Bank, Identification, CreateNationalNumber, IsGroupMember, HCCode, PaymentAgreement, SendMail]
---

# Fonctions de la table Correspondent

Table GLIMS : `crsp` — représente un correspondant (médecin prescripteur, service externe, institution).

---

## SendMail
**Signature** : `Logical SendMail(String From, String Subject, String Content, MailPriority Priority)`  
Envoie un email externe à l'adresse du correspondant.  
`From` : `"USER"`, `"RESPONSIBLE"`, `"SITE"` ou adresse email directe.  
`Priority` : `MailPriority["Low"]`, `MailPriority["Normal"]`, `MailPriority["High"]` (ou 1/2/3).

```mispl
/* Envoyer un résultat critique au médecin prescripteur */
.Action().Order().Correspondent.SendMail(
  "SITE",
  "Résultat critique — Patient " + .Action().Object.LastName,
  "Valeur critique détectée. Veuillez contacter le laboratoire.",
  MailPriority["High"]
);
```

---

## Attribute
**Signature** : `String Attribute(String AttributeName)`  
Lit un attribut personnalisé du correspondant.

---

## Person
**Signature** : `Person Person()`  
Retourne la personne physique associée au correspondant (si le correspondant est une personne).

---

## Fund
**Signature** : `Fund Fund()`  
Retourne la caisse d'assurance liée au correspondant.

---

## Bank
**Signature** : `Bank Bank()`  
Retourne les coordonnées bancaires du correspondant.

---

## HCCode
**Signature** : `String HCCode()`  
Retourne le code identifiant du prestataire de soins (RIZIV/INAMI en Belgique).

---

## Identification
**Signature** : `String Identification(String SourceInternalId)`  
Retourne un identifiant externe du correspondant selon la source spécifiée.

---

## IdentificationList
**Signature** : `String IdentificationList(String SourceInternalId, Date ReferenceDate, String Format)`  
Retourne la liste des identifications actives à une date de référence.

---

## CreateNationalNumber
**Signature** : `Logical CreateNationalNumber(String Code, Date StartDate, Date EndDate)`  
Crée un numéro national (NISS) pour le correspondant.

---

## IsGroupMember
**Signature** : `Logical IsGroupMember(String GroupName)`  
Teste si le correspondant appartient au groupe `GroupName`.

---

## PaymentAgreement
**Signature** : `PaymentAgreement PaymentAgreement(PositiveInteger SequenceNumber, Date ValidityDate)`  
Retourne l'accord de tiers-payant valide à la date spécifiée.

---

## CurrentAgreements
**Signature** : `String CurrentAgreements(Date ValidityDate)`  
Liste les accords de tiers-payant actifs formatés en chaîne.

---

## GroupMembership
**Signature** : `CorrespondentGroupMember GroupMembership(String GroupName, String GroupCode)`  
Retourne l'appartenance au groupe avec le code spécifié.

---

## UnpaidAmount
**Signature** : `Fractional UnpaidAmount(Mnemonic FirmMnemonic, Date MaximumDueDate)`  
Retourne le montant impayé du correspondant avant une date limite.
