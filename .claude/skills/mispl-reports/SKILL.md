# MISPL Reports — Skill pour comptes-rendus et textes GLIMS

## Purpose
Générer les textes MISPL pour comptes-rendus de laboratoire, étiquettes, et rapports PDF GLIMS.
Focus : mise en forme, conditionnels cliniques, fusion de données patient.

## Method
1. Identifier le contexte d'impression (compte-rendu PDF / étiquette / écran)
2. Identifier la table de base (Sample, Patient, Order, Result…)
3. Récupérer les champs accessibles via ERD RAG
4. Construire le texte avec balises GLIMS si applicable
5. Citer source pour chaque fonction de formatage utilisée

## Text vs Expression
- **Textes MISPL** : utilisés dans `report_templates`, `default_reports` — retournent STRING
- **Expressions MISPL** : calculs, validations — retournent n'importe quel type

## Common Report Patterns

### En-tête patient dynamique
```mispl
STRING PROGRAM
  STRING nom, ddn, nip;
  nom := .Patient.LastName + " " + .Patient.FirstName;
  ddn := DateToString(.Patient.BirthDate, "%d/%m/%Y");
  nip := .Patient.ExternalId;
RETURN "Patient : " + nom + " | DDN : " + ddn + " | NIP : " + nip;
```

### Résultat conditionnel avec unité
```mispl
STRING PROGRAM
  STRING res, unite;
  FRACTIONAL val;
  val := .NumericResult;
  IF val = ? THEN
    RETURN "En attente";
  ENDIF;
  unite := .Unit.Mnemonic;
  IF val > .HighLimit THEN
    RETURN FractionalToString(val, "%6.2f") + " " + unite + " [H]";
  ENDIF;
  IF val < .LowLimit THEN
    RETURN FractionalToString(val, "%6.2f") + " " + unite + " [L]";
  ENDIF;
RETURN FractionalToString(val, "%6.2f") + " " + unite;
```

### Étiquette tube formatée
```mispl
STRING PROGRAM
  STRING barcode, dt;
  barcode := .Sample.Barcode;
  dt := DateTimeToString(.Sample.CollectionDateTime, "%d/%m/%Y %H:%M");
RETURN barcode + Chr(10) + dt + Chr(10) + .Patient.LastName;
```
Note : `Chr(10)` = saut de ligne, `Chr(13)` = retour chariot

## Output Format
Même structure que mispl-core/SKILL.md — inclure toujours :
- Source documentaire
- Niveau de certitude
- Avertissement si champ ERD non confirmé dans RAG

## Domain Focus
- Templates de comptes-rendus biochimie, hématologie, microbiologie
- Étiquettes tubes et flacons
- Commentaires interpretatifs conditionnels
- Fusion données multi-examens dans un seul texte
