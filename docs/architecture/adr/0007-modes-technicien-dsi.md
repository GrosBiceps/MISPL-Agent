# ADR-0007 — Modes d'accès Technicien / DSI

## Statut

Accepté.

## Date

2026-08-14 (commit `a0050d6`, `feat(security): mode d'accès DSI/Technicien +
corrections d'audit`, et `71611ea`, `feat(security): access_mode_for_user()
— dérive le mode depuis un compte, sans coupler src/ à api/`). Renforcé le
2026-08-27 (commits `cc4d6dc`, `f73790c`, `9762d8c` — fermeture de
contournements de la barrière de détection des boucles) et le 2026-09-24
(commit `02b3225`, rappel de la consigne mode Technicien dans le prompt
utilisateur, à la suite du banc de test temps réel).

## Contexte

Un technicien de laboratoire n'est généralement pas développeur. Un script
MISPL mal écrit avec une boucle (`WHILE`/`REPEAT`) peut, en cas d'erreur de
condition d'arrêt, provoquer une boucle infinie sur le serveur GLIMS —
serveur partagé par l'ensemble du laboratoire, avec un impact direct sur la
production de résultats. Le code utilisant des boucles est plus risqué à
générer automatiquement sans relecture experte que du code séquentiel simple.

## Décision

Distinguer deux modes de génération :
- **Mode Technicien** (mode par défaut, fail-safe) : la génération de
  boucles `WHILE`/`REPEAT` est interdite.
- **Mode DSI** : génération complète, y compris avec boucles, pour un
  personnel habilité à valider et déployer les scripts en production.

La défense est **en profondeur, à deux couches** :
1. Une consigne dans le prompt système (`TECHNICIEN_PROMPT_RESTRICTIONS` dans
   `src/security/access_mode.py`) demande au LLM de refuser lui-même.
2. Une **barrière post-génération** (`enforce_access_mode`) inspecte la
   réponse produite et la remplace intégralement par un message de refus si
   une boucle apparaît malgré tout — y compris hors d'un bloc de code
   correctement balisé, ou dans une fence générique sans tag `mispl`. Cette
   barrière a été renforcée à plusieurs reprises après des contournements
   identifiés en audit (fence générique sans tag, boucle en dehors de tout
   bloc de code, faux positif sur un accesseur `.Champ` dans une citation de
   source `.htm`).

Deux mécanismes d'attribution du mode coexistent :
- **Streamlit** : mot de passe DSI partagé, dont le hash PBKDF2-HMAC-SHA256
  (200 000 itérations) est stocké dans `.env`
  (`MISPL_DSI_PASSWORD_HASH`/`_SALT`, générés par
  `scripts/set_dsi_password.py`). Sans ce hash configuré, le mode DSI est
  **définitivement inatteignable** (fail-safe explicite documenté dans le
  code).
- **API** : le mode dépend du champ `can_use_dsi_mode` du compte
  (`api/models.py::User`), attribué par un administrateur. La fonction
  `access_mode_for_user()` a été introduite spécifiquement pour dériver le
  mode depuis un compte sans coupler `src/` (moteur partagé) à `api/`
  (spécifique à la plateforme).

## Alternatives étudiées

- **Un seul mode, sans distinction Technicien/DSI** : écarté — le risque de
  boucle infinie sur le serveur partagé a motivé la distinction dès la
  conception de l'authentification par comptes.
- **Confiance uniquement dans la consigne de prompt (sans barrière
  post-génération)** : écarté après audit — les LLM ne respectent pas
  toujours une consigne de prompt, en particulier sous certaines
  formulations de contournement ; la barrière mécanique ne dépend pas du
  comportement du modèle.
- **Bloquer toute mention du mot « boucle » sans distinction contextuelle** :
  écarté — cela bloquait à tort de la prose légitime mentionnant l'absence de
  besoin de boucle (« Aucune boucle WHILE/REPEAT requise »), corrigé par le
  banc de test temps réel du 2026-09-24 (cas ORD-001).

## Conséquences

- Deux mécanismes de mode d'accès à maintenir en parallèle (mot de passe
  partagé Streamlit, droit par compte API) tant que la migration du premier
  vers le second n'est pas engagée.
- La barrière post-génération nécessite un entretien régulier face à de
  nouveaux contournements (fences génériques, pseudo-code non balisé) : trois
  correctifs successifs le 2026-08-27 en témoignent.
- Le mode Technicien reste utilisable pour l'essentiel des besoins (la
  consigne de prompt invite explicitement à chercher une fonction intégrée
  qui rend la boucle inutile avant de refuser).
