# Acteurs et rôles

Ce document décrit qui utilise MISPL Agent, ce que chaque acteur peut faire
et pourquoi. Il distingue les rôles **applicatifs** (gérés dans la base de
comptes de la plateforme API/Next.js : `platform_role` et `can_use_dsi_mode`
dans `api/models.py`) des rôles **organisationnels** (RSSI, DPO) qui
n'ont pas de compte dans l'application mais qui portent une responsabilité
sur le projet.

## Technicien de laboratoire

**Qui** : technicien de biologie médicale qui écrit ou adapte des scripts
MISPL pour des règles de calcul, validations ou comptes-rendus.

**Pourquoi il utilise l'agent** : il n'est pas développeur et n'a pas un
accès simple au manuel GLIMS ; il a besoin d'une réponse fiable, sourcée, et
d'un code qu'il peut proposer à la DSI sans risquer une boucle infinie sur le
serveur GLIMS partagé.

**Ce qu'il peut faire** :
- Se connecter (plateforme API/Next.js) ou lancer l'interface Streamlit.
- Poser des questions MISPL, en mode Technicien par défaut (pas de génération
  de boucle).
- Consulter et supprimer son propre historique de conversations (plateforme).
- Copier le code généré, avec ses sources et son niveau de certitude.

**Ce qu'il ne peut pas faire** : générer du code utilisant des boucles
(`WHILE`/`REPEAT`), voir l'historique ou l'usage d'un autre compte,
administrer les comptes.

## DSI (Direction/Service des Systèmes d'Information)

**Qui** : personnel de la DSI habilité à valider et déployer des scripts
MISPL en production sur le serveur GLIMS.

**Pourquoi elle utilise l'agent** : elle a besoin du code MISPL complet,
y compris avec boucles quand c'est justifié, pour des besoins que le mode
Technicien ne couvre pas (parcours de listes, traitements complexes).

**Ce qu'elle peut faire** : tout ce que peut faire un technicien, plus
générer du code en mode DSI (génération complète, y compris boucles) si le
compte porte `can_use_dsi_mode=true` (plateforme) ou si le mot de passe DSI
partagé a été saisi (Streamlit, mécanisme historique — voir
`docs/architecture/adr/0007-modes-technicien-dsi.md`).

**Ce qu'elle ne peut pas faire (dans l'agent)** : modifier la configuration
GLIMS elle-même (référentiel d'analyses, bornes, création de patients) — ces
opérations sont hors du périmètre MISPL et signalées comme impossibles par
l'agent ; administrer les comptes de la plateforme si elle n'a pas aussi le
rôle Administrateur.

## Administrateur (plateforme API/Next.js)

**Qui** : porte le `platform_role = "admin"` dans la base de comptes.

**Pourquoi** : quelqu'un doit pouvoir créer les comptes, accorder le droit
d'accès au mode DSI, réagir à un compte compromis (réinitialisation de mot de
passe, révocation de sessions) et suivre la consommation de jetons du service
partagé (le LLM gratuit a des limites de débit collectives).

**Ce qu'il peut faire** (routes `api/routers/admin.py`, protégées par
`require_admin`) :
- Créer un compte (`POST /admin/users`), avec mot de passe temporaire généré
  côté serveur.
- Lister les comptes et leur usage agrégé (`GET /admin/users`).
- Modifier un compte : nom, e-mail, rôle, droit `can_use_dsi_mode`, statut
  actif (`PATCH /admin/users/{id}`), avec un garde-fou qui empêche de
  supprimer le dernier compte administrateur actif.
- Réinitialiser le mot de passe d'un compte (`POST
  /admin/users/{id}/reset-password`).
- Révoquer toutes les sessions actives d'un compte (`POST
  /admin/users/{id}/revoke-sessions`).
- Consulter la consommation quotidienne de jetons d'un compte (`GET
  /admin/users/{id}/usage-daily`).

**Ce qu'il ne peut pas faire** : consulter le contenu des conversations d'un
autre utilisateur (l'historique reste privé à son propriétaire — voir
`api/ownership.py`) ; contourner le hachage Argon2id des mots de passe.

## RSSI (Responsable de la Sécurité des Systèmes d'Information)

**Qui** : n'a pas de compte applicatif dédié ; c'est un rôle organisationnel
consulté sur les décisions de sécurité.

**Pourquoi** : valide les choix structurants de sécurité (hachage des mots de
passe, garde-fous DLP, en-têtes HTTP, gestion des sessions) et arbitre les
constats d'audit de sécurité.

**Ce qu'il fait dans ce projet** : a validé le choix de conserver Argon2id
plutôt que bcrypt pour le hachage des mots de passe (décision du
2026-09-24, voir `docs/architecture/adr/0005-argon2id-mots-de-passe.md` et
`docs/securite/`) ; destinataire des rapports d'audit de sécurité.

## DPO (Délégué à la Protection des Données)

**Qui** : n'a pas de compte applicatif ; rôle organisationnel de conformité
RGPD.

**Pourquoi** : bien que l'agent ne soit pas destiné à traiter des données
patient (voir le cahier des charges, section Périmètre), le DLP constitue un
filet de sécurité contre une saisie accidentelle, et les comptes utilisateurs
eux-mêmes (e-mail, nom) sont des données à caractère personnel dont le cycle
de vie (rétention des sessions, des conversations, purge du cache) relève de
la responsabilité du DPO.

**Ce qu'il fait dans ce projet** : est consulté sur la durée de rétention
des sessions journalisées (`MISPL_SESSION_RETENTION_DAYS`), du cache de
réponses (`MISPL_CACHE_RETENTION_HOURS`) et des conversations stockées en
base ; destinataire, avec le RSSI, des constats concernant le DLP.

## Développeur / mainteneur

**Qui** : personne qui modifie le code du projet (agent, RAG, sécurité, API,
frontend) ou la base de connaissances.

**Pourquoi** : fait évoluer le produit tout en préservant les garanties
« zéro hallucination », la sécurité applicative et l'absence de reprise du
manuel éditeur dans la base de connaissances.

**Ce qu'il fait** :
- Modifie `src/agent/`, `src/rag/`, `src/security/`, `api/`, `frontend/`.
- Avant toute modification de `rag_knowledge_base/` : lance
  `tools/check_ip_similarity.py`, reconstruit l'index, relance `pytest` et
  `scripts/eval_retrieval_kb.py` (voir `CLAUDE.md`).
- Incrémente `CACHE_VERSION` ou `RETRIEVAL_PIPELINE_VERSION` selon la nature
  du changement, pour ne jamais servir une réponse obsolète depuis le cache.
- Exécute le banc de test `scripts/claude_harness/` pour valider les
  changements de comportement de l'agent sans dépendre d'un vrai LLM.
- Ne verse jamais dans le dépôt (public) un secret, une donnée CHU, un
  extrait du manuel GLIMS ou le contenu de `DSI/`.

## Matrice rôles × fonctionnalités

| Fonctionnalité | Technicien | DSI | Administrateur | RSSI | DPO | Développeur |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Se connecter (plateforme) | ✅ | ✅ | ✅ | — | — | ✅ (dev local) |
| Poser une question MISPL (mode Technicien) | ✅ | ✅ | ✅ (si compte) | — | — | ✅ |
| Générer du code en mode DSI (avec boucles) | — | ✅ (si droit) | ✅ (si droit) | — | — | ✅ (tests) |
| Consulter / supprimer son propre historique | ✅ | ✅ | ✅ | — | — | ✅ |
| Créer / modifier un compte, gérer `can_use_dsi_mode` | — | — | ✅ | — | — | — |
| Réinitialiser un mot de passe, révoquer des sessions | — | — | ✅ | — | — | — |
| Suivre l'usage (jetons) | — | — | ✅ | — | consultatif | — |
| Reconstruire l'index RAG | — | — | — | — | — | ✅ |
| Contrôler la PI de la base (`check_ip_similarity.py`) | — | — | — | — | — | ✅ |
| Évaluer la fiabilité du retrieval | — | — | — | — | — | ✅ |
| Valider les choix de hachage / sécurité | — | — | — | ✅ | consultatif | proposant |
| Arbitrer la rétention des données personnelles | — | — | — | consultatif | ✅ | applique |

Légende : ✅ = peut faire directement ; « consultatif » = est consulté ou
destinataire sans exécuter l'action lui-même ; « applique » = met en œuvre
la décision arbitrée par le DPO ; « proposant » = peut proposer une évolution
mais la validation reste au RSSI ; — = hors périmètre du rôle.
