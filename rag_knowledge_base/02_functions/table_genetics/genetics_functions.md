---
id: "functions_genetics"
type: "fonction_core"
domaine: "genetique_moleculaire"
langage_proxy: "Progress ABL / OpenEdge"
context: ["all"]
table_abbrev: ["gnte", "lcsr", "vrnr", "vrnt"]
return_type: "String | Logical | Integer | LocusResult | VariantResult"
priority: "medium"
keywords_fr: ["génétique", "examen génétique", "locus", "variant génétique", "résultat locus", "résultat variant", "annotation variant", "classification variant", "père génétique", "approche génétique"]
anti_hallucination: ["GeneticExam, LocusResult, VariantResult sont des tables spécialisées — non disponibles en routine biologie standard"]
tags: [GeneticExam, gnte, LocusResult, lcsr, VariantResult, vrnr, Variant, vrnt, GetApproachList, GetApproachCount, GetLocusResult, GetLocusResultCount, GetFather, RootSpecimen, GetDetailValue, GetGeneticResultDetail, SetAnnotation, SetClassification, GetAnnotation, GetCopyNumberVariant, GetSequenceVariant, CopyAnnotationsToVariant]
---

# Fonctions des tables de Génétique Moléculaire

Tables GLIMS : `gnte` (GeneticExam), `lcsr` (LocusResult), `vrnr` (VariantResult), `vrnt` (Variant).  
**Usage** : Module génétique GLIMS — séquençage NGS, génotypage, CNV. Hors scope routine biochimie/hématologie standard.

---

## GeneticExam (gnte)

### GetApproachCount
**Signature** : `Integer GetApproachCount()`  
Retourne le nombre d'approches génétiques associées à cet examen.

### GetApproachList
**Signature** : `String GetApproachList()`  
Retourne la liste des approches génétiques (mnémoniques) de l'examen.

### GetFather
**Signature** : `GeneticExam GetFather()`  
Retourne l'examen génétique du père (pour les analyses en trio NGS).

### GetLocusResultCount
**Signature** : `Integer GetLocusResultCount(LocusResultStatus MinimalStatus, Integer MinimalSeverity)`  
Compte les résultats de locus selon des critères de statut et sévérité.

### RootSpecimen
**Signature** : `Specimen RootSpecimen()`  
Retourne le prélèvement racine (ADN) associé à l'examen génétique.

```mispl
/* Accéder au prélèvement ADN de l'examen génétique */
Specimen prelevADN;
prelevADN := .GeneticExam.RootSpecimen();
```

---

## LocusResult (lcsr)

### GetDetailValue
**Signature** : `String GetDetailValue(String DetailName)`  
Retourne la valeur d'un détail spécifique du résultat de locus (allèle, zygosité, etc.).

### GetGeneticResultDetail
**Signature** : `GeneticResultDetail GetGeneticResultDetail(String DetailName)`  
Retourne l'objet détail génétique complet pour un nom de détail donné.

---

## VariantResult (vrnr)

### CopyAnnotationsToVariant
**Signature** : `Logical CopyAnnotationsToVariant()`  
Copie les annotations du résultat vers le variant associé.

### GetAnnotation
**Signature** : `String GetAnnotation(String AnnotationName)`  
Lit une annotation spécifique du résultat de variant (pathogénicité, fréquence population, etc.).

### GetDetailValue
**Signature** : `String GetDetailValue(String DetailName)`  
Retourne la valeur d'un détail du résultat variant.

### GetGeneticResultDetail
**Signature** : `GeneticResultDetail GetGeneticResultDetail(String DetailName)`  
Retourne l'objet détail génétique complet.

### SetAnnotation
**Signature** : `Logical SetAnnotation(String AnnotationName, String Value)`  
Définit une annotation sur le résultat de variant.

```mispl
/* Annoter un variant comme pathogène */
.VariantResult.SetAnnotation("Pathogenicity", "Pathogenic");
```

### SetClassification
**Signature** : `Logical SetClassification(Integer ClassificationLevel)`  
Définit le niveau de classification du variant (1=Bénin → 5=Pathogène).

```mispl
/* Classer un variant selon ACMG (1-5) */
.VariantResult.SetClassification(5);   /* 5 = Pathogenic */
.VariantResult.SetClassification(3);   /* 3 = Variant of Uncertain Significance */
```

---

## Variant (vrnt)

### GetAnnotation
**Signature** : `String GetAnnotation(String AnnotationName)`  
Lit une annotation sur le variant (base de données ClinVar, gnomAD, etc.).

### GetCopyNumberVariant
**Signature** : `CopyNumberVariant GetCopyNumberVariant()`  
Retourne les données de variant de nombre de copies (CNV) associées.

### GetSequenceVariant
**Signature** : `SequenceVariant GetSequenceVariant()`  
Retourne les données de variant de séquence (SNV/InDel) associées.

### SetAnnotation
**Signature** : `Logical SetAnnotation(String AnnotationName, String Value)`  
Définit une annotation sur le variant.

### SetClassification
**Signature** : `Logical SetClassification(Integer ClassificationLevel)`  
Définit la classification ACMG du variant (1=Bénin, 2=Probablement bénin, 3=VUS, 4=Probablement pathogène, 5=Pathogène).
