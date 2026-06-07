---
id: "usecase_reflexes_declencheurs"
type: "cas_usage_production"
domaine: "reflexe_analytique"
langage_proxy: "Progress ABL / OpenEdge"
context: ["result", "action"]
table_abbrev: ["rslt", "ord", "actn", "obj"]
return_type: "Logical"
priority: "critical"
keywords_fr: ["réflexe", "déclencher analyse", "ajouter automatiquement", "si résultat anormal", "analyse complémentaire", "PSA PSAL", "Alzheimer", "pédiatrique", "créatinine", "délai", "toxoplasmose", "sévérité", "annuler résultat", "ObjectType person"]
anti_hallucination: ["GetValue n'existe pas → NumericValue ou Attribute('Value')", "CreatePerson impossible"]
source: "fonctions_mispl.xlsx — Production CHU"
tags: [reflex, AddRequest, MarkAsSolicited, NumericValue, StringToFractional, StringToInteger, RelatedResult, AgeInYears, SetManualSeverity, Cancel, EnumeratedToString, ObjectType, Mantissa, PostProcess]
---

# Cas d'usage : Réflexes analytiques automatiques

Ces scripts déclenchent automatiquement des analyses complémentaires en fonction de résultats initiaux.

---

## UC-01 : Réflexe PSA → PSAL (déclencheur entre 3.5 et 10 ng/mL)

**Contexte** : Result. Déclenche si PSA dans une plage critique.

```mispl
LOGICAL PROGRAM
  STRING valeur;
  valeur := .Result.Attribute("Value");
  .Result.MarkAsSolicited();
  IF StringToFractional(valeur) >= 3.5 AND StringToFractional(valeur) < 10 THEN
    .Action().Order().AddRequest("PSAL", ?, YES);
    .AddInternalComment("PSAL déclenché automatiquement", YES);
  ENDIF;
RETURN YES;
```

**Fonctions clés** : `StringToFractional`, `MarkAsSolicited`, `AddRequest`, `AddInternalComment`

---

## UC-02 : Réflexe Alzheimer ratio (vérification ObjectType = person)

**Contexte** : Action. Déclenche uniquement pour les patients humains (pas les animaux ni devices).

```mispl
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

**Fonctions clés** : `EnumeratedToString`, `ObjectType`, `Mantissa`, `AddRequest`

---

## UC-03 : Réflexe bornes PAL pédiatriques (âge <= 19 ans)

**Contexte** : Action. Déclenche pour les mineurs avec valeur numérique non qualifiée.

```mispl
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

**Fonctions clés** : `AgeInYears`, `Mantissa`, `Substr`, `AddRequest`

---

## UC-04 : Réflexe calcul créatinine/temps (résultats liés)

**Contexte** : Result. Déclenche si deux résultats liés ont des valeurs connues.

```mispl
LOGICAL PROGRAM
  IF StringToFractional(.Result.RelatedResult("B_VOLUME_UR").Attribute("Value")) <> ?
    AND StringToFractional(.Result.RelatedResult("B_TEMPS_RECUEIL").Attribute("Value")) <> ?
  THEN
    Action.Order().AddRequest("B_CALC_CREAT_UR", ?, ?);
  ENDIF;
RETURN YES;
```

**Fonctions clés** : `RelatedResult`, `StringToFractional`, `Attribute("Value")`, `AddRequest`

---

## UC-05 : Réflexe délai FNA avec sévérité (>= 4 heures)

**Contexte** : Result. Convertit un délai en minutes, déclenche si critique ET résultat de contrôle présent.

```mispl
LOGICAL PROGRAM
  IF StringToInteger(.Result.Attribute("Value")) >= (4 * 60)
    AND .Action().Order().Result("B_COB_LACT_SG", ?, ?).Id <> ?
  THEN
    .SetManualSeverity(3);
    Action.Order().AddRequest("B_COMM_DELAI_SUP4H", ?, ?);
  ENDIF;
RETURN YES;
```

**Fonctions clés** : `StringToInteger`, `SetManualSeverity`, `AddRequest`, `Order.Result`

---

## UC-06 : Annulation et réouverture d'une analyse (délai hémostase)

**Contexte** : Result. Annule et commente si délai > 6 heures.

```mispl
LOGICAL PROGRAM
  IF StringToInteger(.Result.Attribute("Value")) >= (6 * 60) THEN
    .SetManualSeverity(46);
    Action.Order().AddRequest("B_COMM_DELAI_Sup6h", ?, ?);
  ENDIF;
RETURN YES;
```

**Fonctions clés** : `StringToInteger`, `SetManualSeverity`, `AddRequest`

---

## UC-07 : Ajout multiple de demandes TOXO en une seule Action

**Contexte** : Action. Ajoute 4 analyses sérologie toxoplasmose simultanément.

```mispl
LOGICAL PROGRAM
  Action.Order().AddRequest("A_S_T_IGG_VIDAS_INFO", ?, ?);
  Action.Order().AddRequest("A_S_T_IGM_VIDAS_INFO", ?, ?);
  Action.Order().AddRequest("A_S_T_COMMENTAIRE", ?, ?);
  Action.Order().AddRequest("A_SEROTHEQUE_SUPPORT", ?, ?);
RETURN YES;
```

---

## UC-08 : Impression étiquettes avec PostProcess

**Contexte** : Action. Ajoute une analyse puis déclenche l'impression.

```mispl
LOGICAL PROGRAM
  Action.Order().AddRequest("B", ?, ?);
  Action.Order().PostProcess(?, ?, ?, ?, ?, ?, YES);
RETURN YES;
```

---

## UC-09 : Validation avec sévérité conditionnelle

**Contexte** : Result. Sévérité critique si valeur <= 1 (valeur de panique).

```mispl
LOGICAL PROGRAM
  IF .Result.NumericValue() <= 1 THEN
    .Result.SetManualSeverity(11);
  ELSE
    .Result.SetManualSeverity(0);
  ENDIF;
RETURN YES;
```

---

## UC-10 : Suppression d'un résultat doublon (Cancel conditionnel)

**Contexte** : Result. Annule un résultat existant si un autre résultat lié est présent.

```mispl
LOGICAL PROGRAM
  IF .Result.Order.Result("B_MOD_PRO_SG", "Initial", "Validated").RawValue <> ? THEN
    .Result.Order.Result("B_MOD_PRO_SG", "Initial", "Validated")
      .Cancel("Discontinue", "Protéine Sérique réalisée discontinue la protéine plasmatique");
  ENDIF;
RETURN YES;
```

---

## UC-11 : Déclencheur Alzheimer ratio avec check deux résultats liés

**Contexte** : Result. Pattern alternatif avec `RelatedResult.Id`.

```mispl
LOGICAL PROGRAM
  IF .Result.RelatedResult("B_PROT_BETA_AMYL").Id <> ?
    AND .Result.Mantissa <> ?
  THEN
    Action.Order().AddRequest("B_ALZ_RATIO_ABETA42_40", ?, ?);
  ENDIF;
RETURN YES;
```
