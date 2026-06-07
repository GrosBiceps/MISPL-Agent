# ÉTAPE 1 — Risque sur les Données de Santé (RGPD & HDS)

## 1.0 Statut juridique de l'architecture actuelle — Clarification fondamentale

### Position de la CNIL (recommandation IA générative, avril 2023 + mise à jour 2024)

**Poser une question technique à un LLM cloud (OpenRouter, ChatGPT...) sans données personnelles n'enfreint aucune règle RGPD.** C'est juridiquement identique à une recherche Google ou une question sur Stack Overflow.

### Qualification de l'architecture actuelle

| Composant | Contient des données personnelles ? | Obligation RGPD/HDS |
|---|---|---|
| Base vectorielle (RAG) | **NON** — manuel technique GLIMS uniquement | **Aucune** |
| Questions typiques des utilisateurs | **NON** — paramétrage générique (`"Comment créer un script MISPL qui ajoute réticulocytes si HB < 8 ?"`) | **Aucune** |
| Flux vers OpenRouter/LLM cloud | **NON** si aucun patient nommé | **Aucune** |
| Logs locaux | **NON** si aucune DCPS saisie | **Aucune** |

**Conclusion : l'outil dans son usage nominal (questions de paramétrage pur) est hors champ RGPD et hors champ HDS.** Même depuis un réseau hospitalier, un paramétreur demandant "comment utiliser Order.AddRequest ?" à un LLM cloud ne commet aucune infraction — exactement comme s'il posait la question à ChatGPT.

> La seule obligation résiduelle est **interne** : certains établissements interdisent les services cloud non référencés dans leur PSSI. C'est une règle organisationnelle, pas une obligation légale externe.

### Le risque est comportemental, pas architectural

Le risque réglementaire n'existe **que si** un utilisateur inclut volontairement ou non des DCPS dans son prompt. L'architecture elle-même est neutre. La section suivante documente ce risque résiduel.

---

## 1.1 Analyse du scénario de contamination involontaire

### Nature du risque résiduel

Un utilisateur peut involontairement inclure dans son prompt des **Données à Caractère Personnel de Santé (DCPS)** :
- Numéro IPP / NIP patient
- Résultat d'analyse nominatif ("Le résultat HB de M. Dupont Jean, né 12/03/1965...")
- Identifiant de dossier tracé nominativement
- Données indirectement identifiantes (combinaison âge + pathologie + hôpital)

Ces données constituent des **données de santé** au sens de l'article 9 du RGPD et de la loi Informatique et Libertés modifiée (LIL).

---

## 1.2 Scénario A — Modèle via API Cloud (Hugging Face Inference API, OpenRouter)

### Qualification juridique du flux

Dès qu'une DCPS transite vers un serveur externe non certifié HDS :
- **Traitement de données de santé hors HDS** → violation de l'article L.1111-8 du Code de la Santé Publique (CSP)
- **Transfert hors EEE potentiel** si hébergeur non européen → violation des articles 44-49 RGPD (transferts internationaux)
- **Sous-traitance sans DPA** → violation de l'article 28 RGPD

### Sanctions encourues

| Infraction | Base légale | Sanction maximale |
|---|---|---|
| Traitement données santé hors HDS | Art. L.1111-8 CSP + Art. R.1111-9 | 3 ans d'emprisonnement + 45 000 € (personnes physiques) |
| Violation RGPD (article 83 §5) | RGPD Art. 9 + Art. 83 | 20 M€ ou 4% CA mondial (le plus élevé) |
| Transfert illicite hors EEE | RGPD Art. 44-49 | Même régime Art. 83 §5 |
| Absence de DPA sous-traitant | RGPD Art. 28 | Jusqu'à 10 M€ ou 2% CA |

**La CNIL peut engager une procédure de sanction accélérée** (art. 22 loi RGPD FR) sans mise en demeure préalable pour les violations manifestes impliquant des données de santé.

### Responsabilités

- **Responsable de Traitement** : l'établissement de santé (LBM) — même si l'outil est développé par un tiers
- **Sous-traitant** : le développeur de l'outil + l'hébergeur de l'API
- **Chaîne de sous-traitance** : chaque maillon doit être sous contrat DPA (art. 28 RGPD)

---

## 1.3 Scénario B — Modèle 100% local (poids téléchargés, aucun appel réseau)

### Est-ce que cela résout le problème HDS ?

**Partiellement — mais pas totalement.**

#### Ce qui est résolu :
- ✅ Aucun transfert vers serveur externe → obligation HDS sur la transmission éliminée
- ✅ Aucun risque de transfert hors EEE
- ✅ Pas de sous-traitant tiers impliqué dans le traitement

#### Ce qui reste obligatoire :

**Le poste local hébergeant des données de santé devient lui-même soumis aux exigences HDS** si des DCPS y sont **stockées ou traitées de manière persistante** (logs, cache, historique).

| Obligation | Base légale | Application |
|---|---|---|
| **Politique de sécurité SI** (PSSI) | Art. 32 RGPD + RGS v2.0 | Le poste doit respecter le RGS niveau étoile minimum |
| **Chiffrement des données au repos** | Art. 32 RGPD | Disque chiffré (BitLocker/VeraCrypt) obligatoire |
| **Chiffrement des données en transit** | Art. 32 RGPD | TLS 1.2+ si réseau local |
| **Contrôle d'accès** | Art. 32 RGPD + ISO 27001 | Authentification forte, pas de compte partagé |
| **Journalisation des accès** | Art. 5(2) RGPD (accountability) | Logs d'accès conservés |
| **Procédure de violation** | Art. 33-34 RGPD | Notification CNIL sous 72h si incident |
| **Analyse d'impact (AIPD)** | Art. 35 RGPD | Obligatoire si traitement à grande échelle ou données sensibles |
| **DPO informé** | Art. 37-39 RGPD | Le DPO du LBM doit valider l'architecture |

#### Concernant la certification HDS stricto sensu :

La certification HDS (référentiel ANSSI/ANS, décret 2018-137) s'applique à **l'hébergement** — i.e. à l'infrastructure physique et logique qui stocke les données de manière durable. Un poste de dev en usage ponctuel n'est pas un "hébergeur de données de santé" au sens réglementaire **si et seulement si** :
- Les données de santé ne sont **pas stockées durablement** (pas de base de données patients locale)
- Les logs ne contiennent **aucune DCPS persistante**
- L'outil est en **environnement de développement strictement isolé** sans accès aux données de production réelles

**En environnement de production (données réelles), la certification HDS ou le recours à un hébergeur certifié HDS devient obligatoire** dès qu'une DCPS est traitée, même ponctuellement.

---

## 1.4 Synthèse des risques par scénario

| Scénario | Risque RGPD | Risque HDS | Niveau global |
|---|---|---|---|
| API Cloud, DCPS dans prompt | CRITIQUE | CRITIQUE | 🔴 Interdit |
| API Cloud, aucune DCPS | Faible | Nul | 🟡 Acceptable avec DPA |
| Local, DCPS en prod | Modéré | CRITIQUE si stockage | 🔴 Interdit sans HDS |
| Local, dev isolé, aucune DCPS | Très faible | Nul | 🟢 Acceptable |
| Local, DLP actif bloquant les DCPS | Faible | Faible | 🟢 Cible recommandée |
