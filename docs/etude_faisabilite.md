# Étude de Faisabilité — Agent IA MISPL/GLIMS
## Assistant IA Open-Source pour la Programmation MISPL en Laboratoire de Biologie Médicale

**Version :** 1.0  
**Auteur :** Interne en biologie médicale  
**Date :** Juin 2026  
**Destinataires :** Médecins biologistes responsables, Direction informatique  

---

## 1. Résumé Exécutif

Ce document évalue la faisabilité technique et fonctionnelle d'un agent IA spécialisé dans l'assistance au codage en langage MISPL pour le SIL GLIMS (Clinisys). L'outil proposé est une solution open-source et locale, combinant un moteur de recherche sémantique (RAG) sur la documentation officielle GLIMS et un modèle de langage (LLM) pour la génération de code.

**Proposition de valeur :** Permettre aux techniciens et biologistes du laboratoire de coder des règles métiers MISPL sans expertise préalable approfondie, en réduisant le temps de développement et les erreurs de déploiement.

---

## 2. Contexte et Problématique

### 2.1 MISPL : un langage stratégique mais sous-documenté

MISPL (MIPS Site Programming Language) est le langage propriétaire de GLIMS permettant de personnaliser le comportement du SIL : calcul de résultats dérivés, formatage d'identifiants, règles de validation, génération de comptes-rendus, déclencheurs sur événements.

**Problèmes actuels :**
- Documentation officielle volumineuse (~500 fichiers HTML) et difficile à naviguer
- Pas de complétion automatique ni d'IDE dédié pour MISPL
- Courbe d'apprentissage élevée pour les nouveaux entrants
- La solution IA officielle Clinisys est hors budget pour la majorité des laboratoires

### 2.2 Risques du statu quo

- Dépendance à 1-2 experts internes MISPL (risque de perte de compétence)
- Délais longs pour les nouvelles fonctionnalités (semaines vs heures)
- Erreurs de script en production impactant potentiellement les résultats patients

---

## 3. Architecture Technique Proposée

### 3.1 Stack

| Composant | Technologie | Rôle |
|-----------|-------------|------|
| LLM | Claude Sonnet (API Anthropic) | Raisonnement et génération de code |
| Embeddings | sentence-transformers (local) ou OpenAI | Vectorisation de la documentation |
| Vectorstore | ChromaDB (local, fichiers) | Stockage et recherche sémantique |
| Interface | Claude Code CLI ou interface web future | Interaction utilisateur |
| Langage | Python 3.10+ | Pipeline RAG et agent |

### 3.2 Flux de traitement

```
Question technicien
       ↓
  [RAG Retriever]
  Recherche sémantique dans 
  documentation GLIMS (~3000 chunks)
       ↓
  Top 6 chunks pertinents
       ↓
  [LLM Claude]
  Génération code MISPL
  avec sources citées
       ↓
  Réponse structurée
  + niveau de certitude
  + avertissements cliniques
```

### 3.3 Mode opérationnel

- **100% local possible** : embeddings locaux (sentence-transformers), pas de données patients transmises
- **Hybride** : embeddings OpenAI pour meilleure qualité, LLM Claude via API
- **Données transmises à l'API** : uniquement la question et des extraits de documentation — jamais de données patients

---

## 4. Prérequis Techniques

### 4.1 Infrastructure minimale

| Prérequis | Spécification | Commentaire |
|-----------|---------------|-------------|
| Serveur/PC dédié | 8 Go RAM, 10 Go disque | Pour vectorstore + modèle local |
| Python | 3.10+ | Via conda ou système |
| Accès Internet | Optionnel | Nécessaire pour API Claude/OpenAI uniquement |
| OS | Windows 10/11, Linux, macOS | Multiplateforme |

### 4.2 Accès réseau

- **Mode 100% local** : aucun accès internet requis après installation
- **Mode API** : HTTPS sortant vers api.anthropic.com uniquement (pas de données patients)
- Pas d'accès à GLIMS ni à la base de données SIL

### 4.3 Sécurité et conformité

- Aucune donnée patient n'est traitée par l'agent (entrées = questions en langage naturel + extraits doc)
- Journalisation locale de toutes les sessions (`outputs/sessions/`)
- Code généré = suggestions — validation humaine obligatoire avant déploiement GLIMS
- Aucune écriture directe dans GLIMS possible (outil passif)

---

## 5. Évaluation de la Qualité du Code Généré

### 5.1 Métriques d'évaluation proposées

| Métrique | Méthode | Seuil cible |
|----------|---------|-------------|
| Taux de compilation MISPL | Scripts générés compilant sans erreur dans éditeur GLIMS | ≥ 85% |
| Taux d'hallucination | Fonctions inventées / fonctions totales utilisées | < 5% |
| Pertinence fonctionnelle | Revue manuelle par expert MISPL (score 1-5) | ≥ 4/5 |
| Temps de génération | Latence question → réponse | < 15 secondes |

### 5.2 Protocole de test proposé

**Phase 1 — Tests unitaires (2 semaines)**
- 50 questions MISPL de difficulté croissante avec réponses de référence (ground truth)
- Catégories : fonctions string, dates, conversions, mathématiques, logique conditionnelle
- Validation par l'expert MISPL du laboratoire

**Phase 2 — Tests d'intégration (2 semaines)**
- 20 scripts complets (calcul résultat, formatage identifiant, règle de validation)
- Test de compilation dans l'environnement de développement GLIMS
- Test d'exécution sur données de test anonymisées

**Phase 3 — Pilote utilisateur (4 semaines)**
- 3-5 techniciens pilotes formés (1h)
- Utilisation sur cas réels non urgents
- Recueil feedback via questionnaire standardisé (SUS Score)

### 5.3 Environnement de test requis

- Accès à un environnement GLIMS de développement/recette (non production)
- Droits de création/modification de fonctions configurables MISPL
- Données patients anonymisées ou synthétiques pour les tests d'exécution

---

## 6. Stratégie d'Adoption par les Techniciens

### 6.1 Profil des utilisateurs cibles

| Profil | Niveau MISPL actuel | Bénéfice attendu |
|--------|---------------------|------------------|
| Technicien SIL | Débutant | Autonomie sur scripts simples |
| Biologiste médical | Intermédiaire | Rapidité pour règles métiers |
| Informaticien SIL | Avancé | Revue et optimisation de code existant |

### 6.2 Plan de formation

- **Session de découverte** (1h) : présentation de l'outil, cas d'usage, limites
- **Guide utilisateur** (PDF) : 10 exemples de questions types avec réponses commentées
- **Documentation des limites** : ce que l'agent NE peut pas faire (modification GLIMS, accès données)

### 6.3 Gestion du changement

- Insister sur le rôle d'**assistant, pas de remplaçant** : le code généré doit toujours être relu
- Former sur l'interprétation des niveaux de certitude (✅ / ⚠️ / 🔬)
- Mettre en place un canal de feedback (tickets, formulaire) pour amélioration continue

---

## 7. Analyse de Retour sur Investissement (ROI)

### 7.1 Coûts de la solution proposée

| Poste | Coût estimé | Fréquence |
|-------|-------------|-----------|
| Développement initial (interne) | ~40h × tarif interne | One-shot |
| API Claude Sonnet | ~0,003 USD/1000 tokens | Par usage (~0,01€/question) |
| Maintenance | ~2h/mois | Mensuel |
| Serveur dédié | 0€ (PC existant) | - |
| **Total année 1** | **~200-500€** | Selon volume usage |

### 7.2 Coût de la solution Clinisys officielle

- Devis indicatif : **5 000 – 20 000€/an** selon contrat et modules
- Non accessible à la plupart des laboratoires publics

### 7.3 Gains estimés

| Gain | Estimation | Méthode de calcul |
|------|------------|-------------------|
| Temps développement MISPL | -50% à -70% | Sur scripts simples à intermédiaires |
| Réduction erreurs de déploiement | -30% | Via détection patterns coûteux |
| Formation nouveaux entrants | -30% | Autonomie accélérée |
| **ROI estimé** | **> 10:1** | Comparé à solution Clinisys |

---

## 8. Risques et Mesures d'Atténuation

| Risque | Probabilité | Impact | Mesure |
|--------|-------------|--------|--------|
| Hallucination de fonctions MISPL | Faible (mécanisme RAG + garde-fous) | Élevé (erreur compilation) | Niveau de certitude obligatoire, test systématique |
| Adoption insuffisante | Moyen | Moyen | Formation, cas d'usage concrets, championne utilisateur |
| Coût API dépassant budget | Faible | Faible | Mode local possible, budget < 50€/mois |
| Documentation GLIMS incomplète | Moyen | Moyen | Fallback pseudo-code, enrichissement manuel |
| Dépendance à l'interne développeur | Élevé | Élevé | Documentation complète, code open-source sur Git interne |

---

## 9. Plan de Déploiement

### Calendrier proposé

| Phase | Durée | Livrable |
|-------|-------|---------|
| **P0 — Setup** | 1 semaine | Environnement technique, vectorstore, tests unitaires |
| **P1 — Validation** | 2 semaines | 50 questions testées, rapport qualité |
| **P2 — Pilote** | 4 semaines | 3-5 utilisateurs pilotes, feedback |
| **P3 — Déploiement** | 2 semaines | Mise à disposition laboratoire, formation |
| **P4 — Maintenance** | Continu | Mises à jour documentation, amélioration |

**Durée totale jusqu'au déploiement : ~2 mois**

---

## 10. Recommandations

L'étude de faisabilité conclut à un **feu vert technique et fonctionnel** pour le développement et le déploiement de cet agent IA MISPL, sous réserve de :

1. **Validation hiérarchique** : accord de la Direction Informatique et du Médecin Biologiste responsable du SIL
2. **Accès à l'environnement de développement GLIMS** pour les tests de compilation
3. **Désignation d'un expert MISPL référent** pour la validation du jeu de test ground truth
4. **Politique claire** : le code généré est une aide à la rédaction, jamais un déploiement automatique

La solution est techniquement mature, économiquement viable, et peut être opérationnelle en 2 mois avec les ressources internes disponibles.

---

*Document préparé par l'équipe informatique du laboratoire. Confidentiel — usage interne.*
