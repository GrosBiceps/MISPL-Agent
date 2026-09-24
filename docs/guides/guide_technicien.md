# Guide du technicien de laboratoire

Ce guide s'adresse aux techniciens de biologie médicale qui utilisent MISPL
Agent pour écrire ou comprendre des scripts MISPL du SIL GLIMS.

## Accéder à l'agent

Deux interfaces existent :

- **Plateforme multi-utilisateurs** (recommandée si votre laboratoire l'a
  déployée) : ouvrez l'adresse fournie par votre DSI dans un navigateur, sur
  la page de connexion (`/login`). Vous devez disposer d'un compte, créé par
  un administrateur (voir `guide_dsi_administrateur.md`).
- **Interface Streamlit** (mono-poste) : lancée localement via `.\start.ps1
  run`, accessible sur `http://localhost:8501`.

## Se connecter (plateforme)

1. Saisissez votre e-mail et le mot de passe qui vous a été transmis.
2. Après 5 échecs consécutifs, votre compte est verrouillé 15 minutes — ce
   n'est pas une anomalie, c'est une protection contre les tentatives
   automatisées.
3. Votre session reste active 8 heures, après quoi une nouvelle connexion
   est nécessaire.

## Poser une question

Formulez votre question en français, comme vous le feriez à un collègue :
« Comment tronquer une chaîne de caractères à 10 caractères ? », « Comment
ajouter un commentaire externe sur un résultat ? ». Vous pouvez aussi nommer
directement une fonction MISPL si vous la connaissez.

Un champ optionnel « Contexte labo » permet d'ajouter des précisions
techniques (nom de la table concernée, contrainte particulière). **N'y
saisissez jamais d'information permettant d'identifier un patient** (nom,
date de naissance, numéro de dossier) : un filtre technique (DLP) bloque déjà
les cas les plus manifestes, mais il s'agit d'un filet de sécurité, pas d'une
autorisation à saisir ce type de donnée.

## Lire une réponse

Chaque réponse suit un format fixe :

```
## Contexte GLIMS
[rappel bref du contexte métier]

## Code MISPL
[bloc de code]

## Source
[fichier + section documentaire]

## Niveau de certitude
[✅ Certain | ⚠️ Probable | 🔬 À vérifier]

## Notes techniques
[risques, alternatives, conseils]
```

**Le niveau de certitude n'est pas une formalité.** Il est calculé
automatiquement à partir de la qualité de la documentation retrouvée, et peut
être rétrogradé (par exemple de « ✅ Certain » à « 🔬 À vérifier ») même si
le texte de la réponse semble assuré, dès que la documentation sur laquelle
l'agent s'est appuyé était insuffisante. Un bandeau « ⚠️ Documentation faible
détectée » signale ce cas.

Si l'agent répond « ⚠️ Fonction non trouvée dans la documentation », cela
signifie que la fonction demandée n'existe pas dans sa base de connaissances
— l'agent refuse volontairement d'inventer une fonction. Il propose alors du
pseudo-code à vérifier manuellement dans GLIMS.

**Toujours vérifier la source citée** avant d'utiliser le code proposé : elle
pointe vers un fichier de `rag_knowledge_base/` et une section précise.

## Mode Technicien : pourquoi pas de boucles

Par défaut, votre compte est en **mode Technicien**. L'agent ne génère
jamais de boucle (`WHILE`, `REPEAT`) dans ce mode : une boucle mal maîtrisée
peut provoquer un blocage du serveur GLIMS, partagé par tout le laboratoire.

Si votre besoin semble nécessiter une boucle, l'agent cherche d'abord une
fonction intégrée qui l'évite. S'il n'en trouve pas, il répond :

> 🔒 **Génération réservée au mode DSI**

Dans ce cas, contactez la DSI : soit votre besoin peut être reformulé sans
boucle, soit un script avec boucle doit être écrit et validé par la DSI.

## Consulter et supprimer votre historique

Sur la plateforme, une barre latérale liste vos conversations passées,
regroupées par période. Cliquez sur une conversation pour la rouvrir. Un
bouton « Supprimer » retire définitivement une conversation et tous ses
messages — cette action est irréversible.

Votre historique n'est visible que par vous : un autre technicien ou un
administrateur ne peut pas consulter le contenu de vos conversations (seul
un volume d'usage agrégé, en jetons, est visible par un administrateur).

## Bonnes pratiques

- Copiez le code proposé dans un environnement de test avant tout
  déploiement en production, même en cas de certitude « ✅ Certain ».
- Si une réponse vous semble incorrecte ou dangereuse, ne la déployez pas et
  signalez-le à la DSI, avec un rappel de la question posée.
- Préférez des questions ciblées sur une fonction ou un besoin précis :
  l'agent gère aussi les demandes combinant plusieurs fonctions (« ajouter un
  commentaire externe ET déclencher un e-mail »), mais une question précise
  facilite la vérification de la réponse.
