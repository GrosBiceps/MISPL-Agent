# Guide DSI et administrateur

Ce guide s'adresse à la DSI (utilisatrice en mode complet de génération) et
aux administrateurs de la plateforme (gestion des comptes). Un même compte
peut cumuler les deux rôles.

## Mode DSI — génération complète

Contrairement au mode Technicien (voir `guide_technicien.md`), le mode DSI
autorise la génération de code MISPL avec boucles (`WHILE`/`REPEAT`). Deux
mécanismes coexistent selon l'interface :

- **Plateforme API/Next.js** : le mode dépend du champ `can_use_dsi_mode` de
  votre compte, attribué par un administrateur (voir plus bas). Aucune
  action de votre part n'est nécessaire si ce droit vous a été accordé.
- **Interface Streamlit** : un mot de passe DSI partagé doit être saisi dans
  l'interface. Ce mot de passe est configuré une fois par la DSI via
  `python scripts/set_dsi_password.py` (voir `guide_developpeur.md`). Sans
  cette configuration, le mode DSI est **définitivement inatteignable** sur
  Streamlit (comportement voulu, fail-safe).

**Responsabilité DSI** : le mode DSI lève la restriction anti-boucle, mais
ne dispense pas de relire le code généré avant tout déploiement en
production sur le serveur GLIMS. L'agent ne se connecte jamais lui-même à
GLIMS.

## Administration des comptes (plateforme)

L'administration se fait via la page `/admin` du frontend (réservée aux
comptes `platform_role="admin"`) ou directement via les routes de l'API
(`api/routers/admin.py`).

### Créer un compte

Dans le tableau de bord admin, le formulaire de création demande e-mail, nom
affiché, rôle (`admin` ou `user`) et le droit `can_use_dsi_mode`. Un mot de
passe temporaire est généré côté serveur et affiché **une seule fois** :
transmettez-le à l'utilisateur par un canal sécurisé (jamais par e-mail en
clair si votre politique l'interdit), et l'utilisateur devra le changer à sa
première connexion selon la politique en vigueur.

### Modifier un compte

Le panneau de détail d'un compte permet de modifier son nom, son e-mail, son
rôle et son droit d'accès au mode DSI, ainsi que de le désactiver. Un
garde-fou empêche de désactiver ou de rétrograder **le dernier compte
administrateur actif** — un message d'erreur explicite s'affiche si vous
tentez cette opération, pour éviter de perdre tout accès d'administration.

### Réinitialiser un mot de passe

Le bouton « Réinitialiser le mot de passe » du panneau de détail génère un
nouveau mot de passe temporaire (haché en Argon2id avant stockage) et
l'affiche une seule fois. Combinez systématiquement cette action avec une
**révocation des sessions actives** (bouton séparé) si la réinitialisation
fait suite à une suspicion de compromission — sinon une session déjà ouverte
avec l'ancien mot de passe reste valide jusqu'à son expiration (8 h) malgré
le changement de mot de passe.

### Révoquer les sessions d'un compte

Utile pour forcer une déconnexion immédiate (départ d'un technicien, compte
suspecté compromis, changement de mot de passe). Toutes les sessions actives
du compte sont invalidées ; l'utilisateur devra se reconnecter.

### Suivre l'usage

Le tableau de bord affiche, par compte, un usage agrégé (jetons de prompt,
jetons de complétion, nombre de requêtes) sur une fenêtre glissante, avec un
graphique détaillant la consommation quotidienne et un sélecteur de période.
Ce suivi est utile pour anticiper les limites de débit collectives des
modèles LLM gratuits (voir
`docs/architecture/adr/0002-openrouter-modeles-gratuits-fallback.md`) : si la
consommation approche des seuils habituels de rate-limit, il peut être
pertinent de sensibiliser les utilisateurs ou d'envisager un modèle payant
pour les usages critiques.

## Ce que l'administrateur ne peut pas faire

- Consulter le contenu des conversations d'un utilisateur : seul le volume
  d'usage (jetons, nombre de requêtes) est visible, jamais les questions ou
  réponses elles-mêmes.
- Récupérer un mot de passe en clair : le hachage Argon2id est
  irréversible par construction (voir
  `docs/architecture/adr/0005-argon2id-mots-de-passe.md`). Seule une
  réinitialisation est possible.

## Supervision et exploitation

Pour le déploiement, les variables d'environnement, les sauvegardes, la
rotation des secrets et la procédure en cas d'incident, voir
`docs/guides/exploitation.md`.
