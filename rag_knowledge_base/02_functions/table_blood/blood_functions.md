---
id: "functions_table_blood"
type: "fonction_core"
domaine: "table_blood_transfusion"
langage_proxy: "Progress ABL / OpenEdge"
context: ["all"]
table_abbrev: ["bbag", "bsel"]
return_type: "String | Logical | BloodBag | BloodSelection"
priority: "medium"
keywords_fr: ["poche de sang", "transfusion", "sélection sang", "compatibilité sang", "antigne érythrocytaire", "étiquette poche", "statut poche", "impression bon de distribution", "promotion sang", "temps transfusion"]
anti_hallucination: []
tags: [BloodBag, bbag, BloodSelection, bsel, CreateOrder, Print, SetAntigen, GetAntigen, SetStatus, SetAttribute, Attribute, AttributeOverview, GenerateDocument, CompatibilityCascade, PrintForm, Promotion, SetUtmostTransfusionTime, Successor, LastRequest]
---

# Fonctions des tables BloodBag et BloodSelection

Tables GLIMS : `bbag` (poche de sang), `bsel` (sélection de sang pour transfusion).

---

## BloodBag (bbag) — Poche de sang

### Attribute
**Signature** : `String Attribute(String AttributeName)`  
Lit un attribut de la poche de sang.

### AttributeOverview
**Signature** : `String AttributeOverview(...)`  
Retourne une vue d'ensemble des attributs de la poche.

### CreateOrder
**Signature** : `Logical CreateOrder(...)`  
Crée un dossier de transfusion depuis la poche.

### GenerateDocument
**Signature** : `Logical GenerateDocument(...)`  
Génère un document (bon de distribution) pour la poche.

### GetAntigen
**Signature** : `Logical GetAntigen(String AntigenMnemonic)`  
Lit la présence d'un antigène érythrocytaire sur la poche.

### Lot
**Signature** : `Lot Lot()`  
Retourne le lot associé à la poche.

### Print
**Signature** : `Logical Print(...)`  
Imprime l'étiquette ou la documentation de la poche.

### Selection
**Signature** : `BloodSelection Selection()`  
Retourne la sélection de sang associée à la poche.

### SetAntigen
**Signature** : `Logical SetAntigen(String AntigenMnemonic, Logical Presence)`  
Définit la présence d'un antigène érythrocytaire sur la poche.

### SetAttribute
**Signature** : `Logical SetAttribute(String AttributeName, String Value)`  
Définit un attribut de la poche.

### SetExpirationTime
**Signature** : `Logical SetExpirationTime(DateTime ExpirationTime)`  
Modifie la date d'expiration de la poche.

### SetStatus
**Signature** : `Logical SetStatus(BloodBagStatus NewStatus)`  
Change le statut de la poche (disponible, réservée, transfusée...).

### VerificationPassed
**Signature** : `Logical VerificationPassed(Logical Passed)`  
Marque la vérification pré-transfusionnelle comme effectuée ou non.

---

## BloodSelection (bsel) — Sélection pour transfusion

### CompatibilityCascade
**Signature** : `Logical CompatibilityCascade(...)`  
Lance la vérification de compatibilité en cascade pour la sélection.

### LastRequest
**Signature** : `Request LastRequest(Logical Explicit)`  
Retourne la dernière demande associée à la sélection.

### PrintForm
**Signature** : `Logical PrintForm(...)`  
Imprime le formulaire de sélection / bon de distribution.

### Promotion
**Signature** : `Logical Promotion(...)`  
Promeut la sélection au statut supérieur (validation).

### SetAttribute
**Signature** : `Logical SetAttribute(String AttributeName, String Value)`  
Définit un attribut de la sélection.

### SetUtmostTransfusionTime
**Signature** : `Logical SetUtmostTransfusionTime(DateTime UtmostTime)`  
Fixe l'heure limite de transfusion pour la sélection.

### Successor
**Signature** : `BloodSelection Successor()`  
Retourne la sélection successeur (en cas de remplacement).

---

## Cas d'usage — Vérification sang disponible depuis contexte patient

```mispl
/* Vérifier si du sang est disponible pour ce patient */
LOGICAL PROGRAM
  IF Action.Object.Person().BloodForPersonAvailable("PSC", NO, "BLOC", ?) THEN
    .AddInternalComment("Sang disponible en banque", YES);
  ELSE
    .AddInternalComment("ATTENTION: aucun sang disponible", YES);
  ENDIF;
RETURN YES;
```
