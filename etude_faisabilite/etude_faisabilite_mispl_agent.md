# Étude de faisabilité — Agent IA pour le paramétrage GLIMS / MISPL

**Rédacteur** : Direction Technique (CTO) — IA & Systèmes d'Information de Santé
**Périmètre** : assistant RAG (± fine-tuning) pour la génération et l'explication de code MISPL
**Statut existant** : POC fonctionnel — repo GitHub → Hugging Face Spaces (Docker) → Streamlit, RAG hybride BM25 + ChromaDB, LLM via OpenRouter

---

## 0. Synthèse exécutive (TL;DR)

Le POC actuel **prouve la faisabilité technique**. L'approche **RAG pur est la bonne** ; le fine-tuning est, à ce stade, **inutile et contre-productif**. Le principal risque n'est ni technique ni financier : c'est la **qualité et la sécurité du code généré** dans un contexte clinique. La priorité n'est pas de complexifier l'IA, mais de **durcir la validation** et de **curer drastiquement les données**.

**Recommandation tranchée** : industrialiser le RAG existant + un pipeline de validation strict. Ne PAS fine-tuner avant d'avoir ≥ 500 paires question/réponse validées par un expert. Ne PAS héberger de LLM en interne au lancement.

---

## 1. Faisabilité technique & architecture

### 1.1 Hébergement : Interne vs Cloud/API

| Critère | API Cloud (OpenAI/Anthropic) | Modèle Open Source hébergé interne |
|---|---|---|
| Coût initial | ~0 € (paiement à l'usage) | Élevé (GPU : 1 × A100 ≈ 10–15 k€, ou cloud GPU ~1–2 €/h) |
| Confidentialité données | Données envoyées à un tiers | **Tout reste interne** |
| Qualité modèle | Excellente (GPT-4o, Claude) | Bonne mais inférieure (Llama 70B, Mistral) |
| Maintenance | Nulle | Lourde (MLOps, mises à jour, monitoring GPU) |
| Latence | Réseau + inférence | Inférence locale (potentiellement plus rapide) |

**Point critique confidentialité** : en santé, la question n'est PAS « les données patients fuient-elles ? » — un assistant MISPL ne manipule **pas** de données patients, seulement du **code et de la documentation de paramétrage**. Le risque RGPD/secret médical est donc **faible**, à condition de ne jamais injecter de données patients réelles dans les prompts (exemples, contextes labo). C'est une **règle d'usage**, pas une contrainte d'architecture.

**Verdict** : commencer en **API Cloud** (ou OpenRouter comme aujourd'hui). L'hébergement interne d'un LLM est une sur-ingénierie pour un MVP : coût GPU, compétences MLOps, et maintenance qui ne se justifient que si (a) un volume massif d'usage, ou (b) une contrainte réglementaire formelle interdisant tout appel externe. À réévaluer en phase 2.

> ⚠️ **Nuance sur OpenRouter free tier (existant)** : pratique pour le POC, mais **inadapté à la production** — rate-limits agressifs, latence 4–16 s, modèles qui apparaissent/disparaissent. Pour un MVP en production, passer à un tier payant (OpenRouter payant, ou API directe Anthropic/OpenAI) est nécessaire pour la fiabilité.

### 1.2 Fine-tuning vs RAG pur

**Verdict sans ambiguïté : RAG pur.**

Pourquoi le fine-tuning est une mauvaise idée maintenant :
- **Volume insuffisant** : le fine-tuning utile demande des milliers d'exemples de qualité. La base actuelle est « petite et manque de contexte global » (tes mots). Fine-tuner sur peu de données = sur-apprentissage et hallucinations renforcées.
- **Documentation évolutive** : GLIMS est mis à jour. Le RAG se met à jour en réindexant des fichiers (minutes). Un modèle fine-tuné devrait être ré-entraîné (coûteux, lent).
- **Traçabilité** : le RAG **cite ses sources** (exigence clinique/audit). Un modèle fine-tuné « sait » sans pouvoir prouver d'où vient l'info — inacceptable en santé.
- **Le RAG actuel marche déjà** (recherche hybride + exact-match + reorder).

**Quand reconsidérer le fine-tuning** : seulement si, après plusieurs mois, on dispose de ≥ 500–1000 paires question/réponse **validées par un expert**, ET que le RAG montre une limite récurrente sur le *style* MISPL local (conventions maison). Même alors, privilégier d'abord l'enrichissement du prompt système et des Skills.

### 1.3 Le dilemme du « mauvais code » historique

C'est le **piège central**. Ingérer aveuglément la base de scripts existants = enseigner à l'IA les mauvaises pratiques accumulées (boucles non optimisées, gestion `?` absente, divisions entières dangereuses).

**Stratégie recommandée — tri en 3 niveaux :**

1. **Ne PAS ingérer les scripts bruts dans le RAG de référence.** La doc officielle GLIMS est la source de vérité. Les scripts maison sont une source de *style*, pas de *correction*.
2. **Curation experte** : un biologiste/expert MISPL trie un sous-ensemble de scripts **exemplaires** (20–50 scripts « gold standard »). Ceux-là, et seulement ceux-là, alimentent une base d'exemples séparée.
3. **Anti-pattern library** : les mauvais scripts ne sont pas jetés — ils deviennent une base de **contre-exemples** pour le linter et pour des règles « ne fais jamais X » dans le prompt.

> 💡 Le linter MISPL actuel (détection boucles infinies, division entière, champs read-only) est **l'outil idéal** pour auditer automatiquement la base historique et la classer bon/mauvais avant curation.

### 1.4 Intégration GLIMS profonde (ERD)

Le cœur GLIMS (schéma de base de données, relations entre tables) n'est pas nativement connu de l'agent. C'est une **vraie limite** pour les questions touchant à l'ERD (champs, relations `sample.`, `patient.`, `order.`).

**Faisabilité** : moyenne. Deux options :
- **Court terme (faisable)** : indexer la **documentation de l'ERD** (si elle existe en `.htm`/PDF) comme une catégorie de chunks dédiée — c'est déjà partiellement prévu (`mispl_erd`, skill `erd`).
- **Long terme (complexe)** : connexion read-only à une instance GLIMS pour introspection du schéma. **Déconseillé pour un MVP** : risque sécurité, complexité d'intégration, dépendance à l'environnement. Inutile pour 80 % des cas d'usage (génération de fonctions courantes).

---

## 2. Faisabilité économique

### 2.1 Postes de coûts

| Poste | API Cloud (recommandé MVP) | Hébergement interne |
|---|---|---|
| **Inférence LLM** | 0,01–0,10 €/requête (selon modèle). 1000 req/mois ≈ 10–100 €/mois | Amorti dans le GPU |
| **Infrastructure** | Hugging Face Spaces : gratuit (CPU) à ~9–40 €/mois (upgrade). Ou VM légère ~20 €/mois | GPU : 10–15 k€ achat OU ~700–1500 €/mois cloud |
| **Embeddings** | Locaux (SentenceTransformer) = **0 €** (déjà le cas) | 0 € |
| **Stockage vectorstore** | Négligeable (~150 Mo) | Négligeable |
| **Curation données** (humain) | **Le vrai coût** : ~5–15 j-homme expert pour trier scripts + valider Q/R | Idem |
| **Maintenance MLOps** | Faible | Élevée (0,2–0,5 ETP) |

### 2.2 Lecture économique

Le coût dominant n'est **pas l'infrastructure** — c'est le **temps expert humain** : curation des scripts, validation des réponses, constitution du « gold standard ». Budgéter **ce temps** est la décision financière la plus importante.

Ordre de grandeur MVP réaliste : **< 100 €/mois d'infra+API** + **~10 j-homme expert** de mise en route. L'hébergement interne ferait exploser ce budget (×10–50) sans bénéfice tangible au lancement.

---

## 3. Processus de validation & qualité

**Principe fondateur : l'IA propose, l'humain dispose.** Aucun code MISPL généré ne doit aller en production GLIMS sans validation humaine. L'agent est un **copilote**, pas un déployeur.

### Pipeline de validation à 4 couches

```
Génération IA
   ↓
[1] Linter automatique (déjà en place)
   - Boucles infinies (WHILE TRUE, REPEAT sans UNTIL)
   - Division entière silencieuse (5/2=2)
   - Champs read-only (.Id, .ValidationStatus)
   - Équilibre IF/ENDIF, WHILE/DONE, RETURN présent
   ↓
[2] Traçabilité source obligatoire
   - Chaque fonction citée → fichier .htm source
   - Niveau de certitude affiché (✅/⚠️/🔬)
   - Si fonction non documentée → marquée "à vérifier"
   ↓
[3] Revue humaine par le technicien
   - Lecture du code + des sources
   - Le technicien reste responsable
   ↓
[4] Test en environnement GLIMS de pré-production
   - JAMAIS de premier test en production
   - Validation sur données de test
```

### Garde-fous déjà implémentés (atout fort)
- **Zéro hallucination** : le modèle ne doit utiliser que des fonctions documentées.
- **Strip chain-of-thought** : pas de raisonnement parasite dans la réponse.
- **Niveau de certitude** explicite par réponse.

### À ajouter pour la production
- **Journal d'audit** (déjà partiellement : `outputs/sessions/`) — qui a demandé quoi, quelle réponse, quelles sources. Indispensable en santé.
- **Feedback loop** : bouton « cette réponse était-elle correcte ? » → alimente la curation future.
- **Disclaimer permanent** : « Code à valider par un humain avant déploiement. »

---

## 4. Matrice des risques

| # | Risque | Catégorie | Impact | Probabilité | Stratégie d'atténuation |
|---|---|---|---|---|---|
| R1 | **Code MISPL dangereux déployé en prod** (boucle infinie freeze serveur GLIMS, corruption de données) | Technique/Clinique | **Critique** | Moyenne | Pipeline de validation 4 couches ; linter bloquant sur erreurs ; test obligatoire en pré-prod ; disclaimer |
| R2 | **Hallucination** (fonction inventée) | Technique | Élevé | Moyenne | RAG strict + règle zéro-hallucination + traçabilité source + niveau de certitude |
| R3 | **Apprentissage de mauvaises pratiques** depuis scripts historiques | Technique/Qualité | Élevé | Élevée (si ingestion brute) | NE PAS ingérer scripts bruts ; curation experte ; anti-pattern library |
| R4 | **Indisponibilité LLM** (free tier down, rate-limit) | Technique/Opérationnel | Moyen | **Élevée** (free tier) | Fallback multi-modèles (déjà en place) ; passage tier payant pour la prod ; message d'erreur convivial |
| R5 | **Fuite de données patients** via prompts (exemples avec vraies données) | Sécurité/RGPD | Élevé | Faible | Règle d'usage stricte : jamais de données patients ; anonymisation ; formation utilisateurs |
| R6 | **Documentation obsolète** (GLIMS mis à jour, RAG pas réindexé) | Opérationnel | Moyen | Moyenne | Procédure de réindexation documentée ; date de build affichée ; versioning du cache |
| R7 | **Dépendance fournisseur** (OpenRouter/API change tarifs ou ferme) | Financier/Stratégique | Moyen | Faible | Architecture découplée (SDK OpenAI standard) → bascule facile vers autre fournisseur |
| R8 | **Sur-coût hébergement interne** prématuré | Financier | Moyen | Moyenne (si décision hâtive) | Rester en API Cloud au MVP ; réévaluer l'interne avec données d'usage réelles |
| R9 | **Faible adoption** (techniciens ne font pas confiance / outil trop lent) | Opérationnel | Élevé | Moyenne | UX soignée ; latence acceptable (tier payant) ; sources visibles = confiance ; formation |
| R10 | **Sur-ingénierie** (fine-tuning, intégration ERD profonde au MVP) | Stratégique | Moyen | Moyenne | Discipline produit : RAG pur d'abord, complexité justifiée par les données d'usage |

---

## 5. Recommandations stratégiques

### Avis tranché du CTO

**Ce qui est juste dans l'approche actuelle :**
- RAG hybride (BM25 + dense) : excellent choix, mieux qu'un RAG naïf.
- Embeddings locaux : zéro coût, bonne idée.
- Linter de sécurité : différenciateur fort, à conserver et étendre.
- Traçabilité source : indispensable en santé, déjà là.

**Ce qui est de la sur-ingénierie à éviter pour le MVP :**
- ❌ **Fine-tuning** : inutile avec si peu de données. Reporté.
- ❌ **Hébergement LLM interne** : coût/maintenance disproportionnés. API Cloud suffit.
- ❌ **Intégration GLIMS profonde (connexion DB live)** : complexe, risqué, inutile pour 80 % des cas. Se contenter d'indexer la doc ERD.

**Ce qui manque et doit être priorisé :**
1. **Curation des données** (le vrai travail) — tri expert des scripts, gold standard.
2. **Fiabilisation LLM** — sortir du free tier pour la prod.
3. **Validation humaine formalisée** — pipeline 4 couches, audit, feedback.

### Feuille de route MVP (3 phases)

**Phase 1 — Industrialiser l'existant (1–2 mois)**
- Passer le LLM en tier payant fiable.
- Curer la doc GLIMS (qualité des chunks) + indexer l'ERD documenté.
- Formaliser le pipeline de validation + journal d'audit.
- Déployer auprès de 2–3 utilisateurs pilotes (biologistes référents).

**Phase 2 — Enrichir par l'usage (3–6 mois)**
- Collecter le feedback (bouton correct/incorrect).
- Constituer le gold standard Q/R depuis les vrais usages.
- Étendre le linter avec les anti-patterns historiques.
- Élargir le déploiement.

**Phase 3 — Optimiser (au-delà, si justifié par les données)**
- Réévaluer fine-tuning SI ≥ 500 paires validées ET limite de style avérée.
- Réévaluer hébergement interne SI volume/réglementation l'imposent.

### Conclusion

Le projet est **faisable, pertinent et déjà bien engagé**. Le danger n'est pas technique — c'est la tentation de complexifier (fine-tuning, interne, intégration profonde) avant d'avoir maîtrisé le **socle qualité/validation**. Un MVP discipliné, centré sur le RAG existant + une validation humaine rigoureuse + une curation experte, est la voie la plus sûre et la plus rapide vers un outil réellement utilisé en production hospitalière.
