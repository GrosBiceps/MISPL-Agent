---
id: "functions_interactive"
type: "fonction_core"
domaine: "interactions_utilisateur"
langage_proxy: "Progress ABL / OpenEdge"
context: ["all"]
table_abbrev: null
return_type: "Void | Integer | String | Logical"
priority: "medium"
keywords_fr: ["afficher message", "message utilisateur", "boîte de dialogue", "demander choix", "demander texte", "demander confirmation", "oui non", "dialogue interactif", "alerte"]
anti_hallucination: ["Message() est Void — ne pas tenter de récupérer sa valeur de retour", "AskChoice/AskString/AskYesNo bloquent le thread principal — utiliser avec précaution dans les contextes batch"]
tags: [Message, AskChoice, AskString, AskYesNo, interactif, dialogue, message, alerte]
---

# Fonctions interactives MISPL

**Avertissement** : `AskChoice`, `AskString`, `AskYesNo` bloquent tous les utilisateurs jusqu'à réponse en contexte interactif critique. En mode batch (broker, scheduleur), la réponse par défaut est utilisée automatiquement — toujours prévoir une valeur par défaut.

---

## Message
**Signature** : `Void Message(String MessageString)`  
Affiche un message informatif à l'écran. Ne retourne aucune valeur.  
**Utilisé en production** dans `B_declencheurPSAL` pour alerter l'utilisateur.

```mispl
/* Alerte visuelle lors d'un déclenchement automatique */
message("PSA Compris entre 3.5 et 10 ng/ml ! Un PSAL est rajouté au dossier");
```

**Note** : `message()` en minuscules et `Message()` sont équivalents (MISPL est insensible à la casse sur les fonctions).

---

## AskChoice
**Signature** : `Integer AskChoice(String Question, String Titre, String ListeChoix, Logical Obligatoire, Integer RéponseParDéfaut)`  
Affiche une boîte de dialogue avec une liste de choix. Retourne l'index (base 1) du choix sélectionné.

| Paramètre | Type | Description |
|-----------|------|-------------|
| `Question` | String | Texte de la question |
| `Titre` | String | Titre de la fenêtre (optionnel) |
| `ListeChoix` | String | Valeurs séparées par virgules |
| `Obligatoire` | Logical | YES = pas d'annulation possible |
| `RéponseParDéfaut` | Integer | Index de la réponse par défaut (batch) |

```mispl
INTEGER choix;
choix := AskChoice("Quel tube utiliser ?", "Sélection tube",
                   "EDTA,Citrate,Héparine", NO, 1);
/* choix = 1 si EDTA sélectionné */
```

---

## AskString
**Signature** : `String AskString(String Question, String Titre, Logical Obligatoire, String RéponseParDéfaut)`  
Affiche une boîte de saisie. Retourne le texte saisi par l'utilisateur.

```mispl
STRING commentaire;
commentaire := AskString("Motif de non-conformité ?", "Non-conformité",
                         YES, "Délai dépassé");
```

---

## AskYesNo
**Signature** : `Logical AskYesNo(String Question, String Titre, Logical Obligatoire, Logical RéponseParDéfaut)`  
Affiche une boîte Oui/Non. Retourne YES ou NO.

```mispl
LOGICAL confirme;
confirme := AskYesNo("Confirmer l'annulation du résultat ?",
                     "Confirmation", YES, NO);
IF confirme THEN
  .Cancel("Discontinue", "Annulé par utilisateur");
ENDIF;
```

---

## Cas d'usage CHU — Message dans B_declencheurPSAL

```mispl
/* B_declencheurPSAL : alerte visuelle + déclenchement PSAL */
LOGICAL PROGRAM
  LOGICAL start;
  STRING valeur, a_com_commentaire;

  /* Toutes déclarations en tête obligatoirement */
  valeur := .Result.Attribute("value");    /* insensible à la casse */
  start := NO;
  .Result.MarkAsSolicited();

  IF StringToFractional(valeur) >= 3.5 AND StringToFractional(valeur) < 10 THEN
    start := YES;
    /* Message interactif visible par l'utilisateur déclenchant l'analyse */
    message("PSA Compris entre 3.5 et 10 ng/ml ! Un PSAL est rajouté au dossier du patient");
  ENDIF;

  IF start THEN
    Action.Order().AddRequest("PSAL", ?, ?);    /* forme alternative avec point implicite */
    a_com_commentaire := "PSAL déclenché automatiquement";
    .Result.AddInternalComment(a_com_commentaire, YES);
  ENDIF;
RETURN YES;
```
