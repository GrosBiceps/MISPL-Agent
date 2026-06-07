# ÉTAPE 3 — Qualification comme Dispositif Médical (DM)

## 3.1 Cadre réglementaire applicable

- **Règlement (UE) 2017/745 (MDR)** — applicable depuis le 26 mai 2021
- **Guide MDCG 2019-11** : guidance sur la qualification des logiciels comme DM
- **Guide MDCG 2021-6** : illustration des principes par exemples pratiques
- **Position ANSM** : clarifications françaises sur les SaMD (Software as Medical Device)

---

## 3.2 Critères de qualification DM pour un logiciel

Selon l'**article 2(1) MDR** et l'**annexe XVI**, un logiciel est qualifié DM s'il :

> "est destiné par le fabricant à être utilisé, seul ou en association, chez l'homme à des fins médicales de diagnostic, prévention, contrôle, prédiction, pronostic, traitement ou atténuation d'une maladie..."

Le critère clé est la notion de **"destination médicale directe"** (intended purpose).

---

## 3.3 Analyse de l'outil MISPL Agent

### L'outil génère-t-il des informations à finalité diagnostique ou thérapeutique ?

| Question | Réponse | Justification |
|---|---|---|
| Pose-t-il un diagnostic ? | **NON** | Il génère du code MISPL, pas d'interprétation clinique |
| Fournit-il des valeurs de référence ? | **NON** | Il cite les seuils de la documentation technique GLIMS |
| Prédit-il un état de santé ? | **NON** | Aucune inférence clinique sur des données patient |
| Recommande-t-il un traitement ? | **NON** | Il propose du paramétrage logiciel, pas de conduite clinique |
| Contrôle-t-il directement un équipement médical ? | **NON** | Interface avec GLIMS uniquement |

### Qualification selon MDCG 2019-11

Le guide MDCG 2019-11 distingue :

**Catégorie A — Logiciel DM** : fournit des informations utilisées pour prendre des décisions de diagnostic ou thérapeutiques.

**Catégorie B — Logiciel non-DM** : assiste la gestion, le paramétrage ou l'administration d'un système sans impact direct sur les décisions cliniques.

**L'outil MISPL Agent appartient à la Catégorie B** :
- Il **paramètre un logiciel** (GLIMS) qui lui-même n'est pas un DM au sens diagnostique
- Il **n'analyse pas de données patients** pour produire une information médicale
- La **décision clinique finale** reste intégralement sous la responsabilité du biologiste
- Il s'apparente à un **outil de développement / IDE assisté par IA** pour un SIL

### Critères d'exclusion explicites

Le **considérant 19 du MDR** exclut expressément :

> "Les logiciels destinés à des usages généraux, même lorsqu'ils sont utilisés dans un contexte de soins de santé, et les logiciels destinés à des usages liés au mode de vie et au bien-être ne sont pas des dispositifs médicaux."

L'outil MISPL Agent est un **outil de développement à usage général** appliqué au contexte de la biologie médicale. Il ne devient pas DM par ce seul contexte.

---

## 3.4 Risque de requalification — Zones grises

### Risque 1 : Scripts générant des règles de validation automatique

Si l'outil génère des scripts qui **déclenchent automatiquement des actions cliniques** (ex: validation automatique de résultats, `Result.SetAutomaticValidation(YES)`), une **chaîne causale directe** entre l'outil et une décision clinique pourrait être argumentée.

**Mitigation** : le script doit toujours **maintenir la supervision humaine** (biologiste validant en dernier ressort). La procédure VAB/VAF (§ COFRAC) suffit à documenter ce contrôle humain.

### Risque 2 : Évolution vers un outil de recommandation clinique

Si l'outil évolue pour recommander des **seuils cliniques** ou des **stratégies de reflex testing** basées sur des données épidémiologiques, la qualification DM devrait être réévaluée.

**Recommandation** : définir contractuellement et dans l'IFU (Instructions For Use) les **limites d'usage** de l'outil, notamment l'interdiction de l'utiliser pour des décisions cliniques directes.

---

## 3.5 Conclusion sur la qualification DM

| Critère | Statut |
|---|---|
| Destination médicale directe | ❌ Absent |
| Analyse de données patient | ❌ Absent (base de connaissances = manuel technique) |
| Décision diagnostique ou thérapeutique | ❌ Absent |
| Qualification DM (MDR Art. 2) | **NON APPLICABLE** |
| Marquage CE DM requis | **NON** |
| Enregistrement EUDAMED requis | **NON** |

**L'outil n'est pas un Dispositif Médical** au sens du MDR 2017/745. Il ne nécessite pas de marquage CE DM ni d'enregistrement EUDAMED.

> ⚠️ **Cette qualification doit être réévaluée si les fonctionnalités évoluent** vers une assistance à la décision clinique directe (ex: recommandation de conduite à tenir basée sur des données patient en temps réel).
