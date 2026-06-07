# ÉTAPE 2 — Exigences COFRAC / ISO 15189

## 2.1 L'outil IA doit-il être validé selon ISO 15189 ?

### Réponse : OUI — avec nuance selon le périmètre d'usage

La norme **ISO 15189:2022** (et son prédécesseur 2012, encore applicable pour les accréditations en cours) impose au chapitre **§6.6 "Systèmes d'information du laboratoire" (SIL)** que tout système informatique utilisé dans le cadre des activités analytiques soit **validé avant mise en service**.

#### Critères déclenchant l'obligation de validation

| Critère | Applicable à l'outil ? | Justification |
|---|---|---|
| Génère ou modifie des règles de traitement de résultats | **OUI** | Les scripts MISPL peuvent modifier la logique de validation, de reflex testing, d'ajout de demandes |
| Influence le rendu des résultats au clinicien | **OUI indirect** | Un script mal généré peut créer des faux ajouts de demandes ou bloquer des résultats |
| Fait partie du SIL (GLIMS) | **OUI indirect** | L'outil paramètre GLIMS qui est lui-même le SIL accrédité |
| Outil purement administratif sans impact analytique | **NON** | Non applicable ici |

**Conclusion** : L'outil entre dans le champ du §6.6 ISO 15189 car il **paramètre le SIL accrédité**. Il ne produit pas lui-même de résultats, mais ses sorties (scripts MISPL) modifient le comportement du système accrédité.

### Distinction importante : validation de l'outil vs validation de ses sorties

| Objet de la validation | Obligation | Fréquence |
|---|---|---|
| L'outil IA lui-même (fonctionnement, fiabilité) | **Documentation requise** (procédure de validation logicielle) | À la mise en service + à chaque mise à jour majeure |
| Chaque script MISPL généré par l'outil | **Validation obligatoire avant production** (VAB/VAF) | À chaque nouveau script ou modification |

---

## 2.2 Procédures de vérification imposées aux techniciens

### Cadre normatif applicable

- **ISO 15189:2022 §6.6.3** : "Le laboratoire doit valider les systèmes d'information avant leur mise en service"
- **ISO 15189:2022 §6.6.4** : "Des procédures doivent être établies pour assurer l'intégrité des données"
- **Guide technique COFRAC LAB GTA 26** : validation des SIL et logiciels de laboratoire
- **SH GTA 03** (accréditation biologie médicale) : exigences spécifiques validation logicielle

### Procédures VAB (Vérification Analytique de Base) / VAF (Vérification Analytique Finale)

#### ÉTAPE A — Validation documentaire (avant tout test)

```
☐ 1. Revue du script par un biologiste médical responsable
      - Vérification de la logique clinique (seuils, mnémoniques)
      - Validation de l'intent médical (le script fait-il ce qui est attendu ?)
      
☐ 2. Traçabilité de la génération IA
      - Conserver la question posée à l'outil
      - Conserver la réponse brute de l'outil
      - Identifier le modèle LLM utilisé et sa version
      - Horodatage et identification de l'auteur
      
☐ 3. Revue du code MISPL par un paramétreur confirmé (non générateur)
      - Vérification syntaxique
      - Vérification des mnémoniques (correspondent-ils au référentiel local ?)
      - Vérification des paramètres (seuils, conditions, tables ciblées)
```

#### ÉTAPE B — Tests en environnement de recette (obligatoire)

```
☐ 4. Déploiement dans l'environnement de RECETTE GLIMS (jamais en prod directement)
      - Base de données de test avec données anonymisées
      - Environnement identique à la production (même version GLIMS)
      
☐ 5. Tests fonctionnels (cas nominaux)
      - Cas où la condition est vraie → vérifier que l'action attendue se déclenche
      - Cas où la condition est fausse → vérifier qu'aucune action parasite ne se déclenche
      
☐ 6. Tests aux limites (cas limites)
      - Valeur exactement au seuil (ex: HB = 8.0 g/dL)
      - Valeur inconnue (?) → vérifier le comportement
      - Dossier vide / sans résultats → vérifier pas d'erreur
      
☐ 7. Tests de régression
      - Les fonctionnalités existantes non ciblées sont-elles impactées ?
      - Les CR existants sont-ils toujours générés correctement ?
      
☐ 8. Documentation des résultats de test
      - Rapport de tests avec résultats attendus vs obtenus
      - Signature du testeur + biologiste validateur
```

#### ÉTAPE C — Mise en production contrôlée

```
☐ 9. Autorisation de mise en production signée par le Biologiste Médical Responsable
      (conforme à l'art. L.6213-7 CSP sur la responsabilité du biologiste)
      
☐ 10. Déploiement avec traçabilité (qui, quand, quoi)
       - Enregistrement dans le registre des modifications du SIL
       - Archivage du script MISPL versionné

☐ 11. Surveillance post-déploiement (J+7 minimum)
       - Vérification que les KPIs analytiques ne sont pas impactés
       - Surveillance des incidents (alertes, doublons de demandes...)
       
☐ 12. Plan de retour arrière (rollback)
       - Procédure écrite pour désactiver le script si anomalie détectée
       - Délai maximal d'intervention défini
```

---

## 2.3 Documentation requise pour l'accréditation COFRAC

| Document | Contenu | Responsable |
|---|---|---|
| **Procédure de validation des scripts IA** | Les 12 étapes ci-dessus | Responsable Qualité |
| **Fiche d'utilisation de l'outil IA** | Limites, avertissements, cas d'usage autorisés | Biologiste Médical |
| **Registre des scripts générés** | Traçabilité complète (question, réponse, valideur, date) | Paramétreur |
| **Rapport de validation par script** | Tests effectués, résultats, signature | Testeur + Biologiste |
| **Analyse de risque de l'outil** | AMDEC ou équivalent sur les risques de mauvaise génération | Responsable Qualité |

---

## 2.4 Cas particulier : script modifiant la validation des résultats

Si le script MISPL impacte directement la **validation analytique** (ex: `Result.SetAutomaticValidation`, `Result.SetManualSeverity`, règles de reflex testing), des exigences **supplémentaires** s'appliquent :

- **Validation métrologique** : vérifier que les seuils utilisés (ex: HB < 8 g/dL) sont concordants avec les intervalles de référence validés du laboratoire
- **Notification au COFRAC** si modification substantielle du SIL affectant la portée d'accréditation (selon les termes du contrat d'accréditation)
- **Évaluation d'impact sur l'incertitude de mesure** si le script modifie les règles d'alerte sur des analyses critiques
