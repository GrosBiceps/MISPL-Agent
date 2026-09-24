# Note au RSSI : hachage des mots de passe de MISPL Agent

- Date : 2026-09-24
- Objet : justifier le maintien d'Argon2id (et non bcrypt) pour le stockage des mots de passe, et décrire les garanties obtenues.
- Périmètre : comptes de l'API (FastAPI, interface Next.js) et mot de passe DSI de l'interface historique Streamlit.
- Décision de l'utilisateur (2026-09-24) : conserver Argon2id. Objectif : qu'aucun mot de passe ne puisse jamais être retrouvé.

> Les références réglementaires ci-dessous sont citées de mémoire et avec prudence. Elles sont à vérifier par le RSSI (et le DPO pour la partie RGPD) dans leur version en vigueur avant toute reprise dans un document opposable.

---

## 1. Synthèse

1. Aucun mot de passe n'est stocké, ni en clair ni chiffré. La base ne contient qu'une empreinte Argon2id, calculée avec un sel aléatoire propre à chaque compte. Cette empreinte ne permet pas de retrouver le mot de passe.
2. Paramètres retenus : Argon2id, 64 Mio de mémoire, 3 passes, parallélisme 4, sel de 128 bits, empreinte de 256 bits. C'est le second profil recommandé par la RFC 9106, et il dépasse le minimum de l'OWASP.
3. Un mot de passe oublié ne peut pas être récupéré, par personne, pas même par l'administrateur ou l'éditeur. Le seul recours est une réinitialisation par un administrateur. Elle produit un mot de passe temporaire, affiché une seule fois, que l'utilisateur doit remplacer à sa première connexion.
4. Aucune loi n'impose un algorithme précis. Les textes (RGPD, CNIL, ANSSI, référentiels santé) demandent une fonction non réversible, lente et salée, à l'état de l'art. Argon2id remplit cette exigence mieux que bcrypt.

## 2. Cadre réglementaire (à vérifier par le RSSI)

Aucun texte applicable n'impose Argon2id, bcrypt ou un autre algorithme nommé. Ils fixent une obligation de moyens proportionnés au risque et renvoient à l'état de l'art.

| Texte | Ce qu'il demande, en substance | Lien avec ce projet |
|---|---|---|
| RGPD, article 32 | Des mesures techniques et organisationnelles appropriées au risque, garantissant notamment la confidentialité des données. | Les identifiants (email, mot de passe) sont des données personnelles. Le contexte hospitalier élève le niveau de risque. |
| CNIL, délibération n° 2022-100 du 21 juillet 2022 (recommandation relative aux mots de passe) | Ne jamais conserver un mot de passe en clair. Le transformer par une fonction non réversible et sûre, avec un sel. Viser une entropie suffisante, modulée selon les mesures complémentaires (restriction des tentatives, par exemple). Imposer le renouvellement d'un mot de passe temporaire. | Hachage Argon2id salé, verrouillage après échecs, limitation du débit, changement forcé du mot de passe temporaire. Les seuils d'entropie exacts et leurs exemples sont à relire dans la délibération. |
| ANSSI, *Recommandations relatives à l'authentification multifacteur et aux mots de passe* (v2.0, 2021) | Stocker les mots de passe sous une forme transformée par une fonction de dérivation lente et salée, conçue pour cet usage. À ma connaissance, le guide cite Argon2id et scrypt parmi les fonctions adaptées : à confirmer dans la version en vigueur. Il privilégie aussi la longueur du mot de passe plutôt que des règles de composition complexes. | Choix d'Argon2id. Politique qui accepte une phrase de passe longue sans exiger de familles de caractères. |
| PGSSI-S (Agence du numérique en santé), notamment le référentiel d'authentification des acteurs de santé | Des niveaux d'exigence d'authentification selon la sensibilité de l'accès aux données de santé. | MISPL Agent n'est pas conçu pour traiter des données patient (un filtre DLP bloque les identifiants patient). La PGSSI-S reste le référentiel de l'établissement : le RSSI jugera si un second facteur est attendu. |
| Référentiel de certification HDS (Code de la santé publique, art. L.1111-8) | Si des données de santé à caractère personnel sont hébergées pour le compte d'un tiers, l'hébergeur doit être certifié HDS. Le référentiel s'appuie sur l'ISO 27001 (gestion des accès, cryptographie, journalisation). | À qualifier par le DPO et le RSSI : l'outil n'a pas vocation à héberger des données de santé, mais les conversations pourraient en contenir par erreur (voir le rapport d'audit, section base de données). |

## 3. Pourquoi Argon2id plutôt que bcrypt

| Critère | Argon2id | bcrypt |
|---|---|---|
| Origine | Vainqueur de la Password Hashing Competition (2015). Normalisé par l'IETF dans la RFC 9106 (2021). | Conçu en 1999. Aucune normalisation IETF. |
| Résistance aux GPU et ASIC | Forte : le coût en **mémoire** est réglable (64 Mio par calcul ici). Un attaquant ne peut pas paralléliser massivement des milliers d'essais sur une carte graphique sans disposer de la mémoire correspondante. | Moyenne : bcrypt n'utilise que 4 Kio de mémoire. Il résiste mieux que PBKDF2, mais des matériels spécialisés (FPGA) l'accélèrent nettement. |
| Canaux auxiliaires | La variante « id » combine la protection contre les attaques par canal auxiliaire (Argon2i, première passe) et la résistance aux compromis temps-mémoire (Argon2d). | Non conçu pour cela. |
| Longueur du mot de passe | Aucune limite pratique (ici 256 caractères au maximum, borne fixée par l'API). | **Tronque silencieusement au-delà de 72 octets.** En UTF-8, une phrase de passe accentuée peut dépasser 72 octets avant 72 caractères, et la fin est alors ignorée. |
| Recommandations actuelles | Premier choix de l'OWASP (*Password Storage Cheat Sheet*). Cité par l'ANSSI (à vérifier, voir § 2). | L'OWASP le réserve aux systèmes existants qui ne peuvent pas utiliser Argon2id ou scrypt. |
| Évolutivité | Mémoire, passes et parallélisme sont réglables séparément et encodés dans chaque empreinte, ce qui permet une migration progressive (voir § 4.3). | Un seul paramètre (le « cost »). |

Passer à bcrypt ferait donc perdre la résistance apportée par la mémoire, et ajouterait la troncature à 72 octets. Rien ne justifie ce retour en arrière.

## 4. Paramètres retenus et justification

### 4.1 Valeurs

Source unique : `src/security/password_hashing.py`. Elle est utilisée par l'API (`api/security.py`) et par le mot de passe DSI de Streamlit (`src/security/access_mode.py`).

| Paramètre | Valeur | Référence |
|---|---|---|
| Variante | Argon2id, version 0x13 (19) | RFC 9106, variante recommandée |
| Mémoire (`m`) | 65 536 Kio (64 Mio) | RFC 9106, second profil recommandé (§ 4) |
| Passes (`t`) | 3 | RFC 9106, second profil recommandé |
| Parallélisme (`p`) | 4 | RFC 9106, second profil recommandé |
| Sel | 16 octets (128 bits), aléatoires pour chaque empreinte (générateur du système) | RFC 9106 : 128 bits recommandés |
| Empreinte | 32 octets (256 bits) | RFC 9106 : 256 bits recommandés |
| Bibliothèque | `argon2-cffi` 25.1.0 (liaison vers l'implémentation de référence) | `requirements.txt` |

Minimum de l'OWASP pour Argon2id : m = 19 Mio, t = 2, p = 1. La configuration retenue le dépasse sur les trois axes. Le test `tests/api/test_password_lifecycle.py::TestArgon2Parameters::test_parameters_meet_owasp_minimum` le vérifie.

### 4.2 Pourquoi ces valeurs et pas plus

- Coût mesuré sur le poste de développement : environ **86 ms** par vérification (médiane de 10 mesures, de 79 à 101 ms, 2026-09-24). Un utilisateur légitime ne remarque pas ce délai à la connexion. Pour un attaquant, chaque essai coûte 64 Mio de mémoire et plusieurs dizaines de millisecondes par cœur.
- Mémoire : chaque connexion mobilise 64 Mio pendant son calcul. La limitation du débit (10 tentatives par compte et 30 par adresse IP sur 5 minutes) plafonne le nombre de calculs simultanés, ce qui protège le serveur d'un épuisement mémoire volontaire.
- Les paramètres sont **figés dans le code** au lieu d'être hérités des valeurs par défaut de la bibliothèque. Une mise à jour d'`argon2-cffi` ne peut donc pas les modifier à notre insu.

### 4.3 Évolution sans interruption (re-hachage transparent)

Chaque empreinte embarque ses propres paramètres (format PHC : `$argon2id$v=19$m=…,t=…,p=…$sel$empreinte`). Si le RSSI demande un jour de les renforcer :

1. on modifie les constantes de `src/security/password_hashing.py` ;
2. à chaque connexion réussie, seul moment où le mot de passe en clair est connu, `api/auth.py` détecte que l'empreinte a été produite avec d'anciens paramètres (`check_needs_rehash`) et la recalcule. L'événement `password_rehashed` est inscrit au journal d'audit ;
3. aucune réinitialisation en masse n'est nécessaire.

Le même mécanisme couvre le mot de passe DSI de Streamlit. L'ancien format PBKDF2-HMAC-SHA256 (200 000 itérations) reste accepté, mais un avertissement journalisé, et affiché en mode DSI, invite à le regénérer avec `scripts/set_dsi_password.py`, qui produit désormais une empreinte Argon2id.

### 4.4 Politique de mot de passe (`api/security.py::password_policy_errors`)

- Au moins 12 caractères mêlant 3 familles (minuscules, majuscules, chiffres, caractères spéciaux), **ou** une phrase de passe d'au moins 16 caractères (longueur privilégiée, conformément à l'esprit du guide de l'ANSSI) ;
- au plus 256 caractères ;
- refus des mots de passe triviaux (liste courte intégrée) et de ceux qui contiennent l'identifiant ou le nom de l'utilisateur ;
- le nouveau mot de passe doit différer de l'actuel ;
- les messages d'erreur ne reprennent jamais le mot de passe saisi.

Ordre de grandeur, à confronter aux seuils de la délibération CNIL 2022-100 : 12 caractères tirés de 3 familles (environ 70 symboles) donnent au plus environ 73 bits. Une phrase de 16 caractères ou plus dépend des mots choisis. La délibération module l'entropie exigée selon les mesures complémentaires, ici le verrouillage après 5 échecs pendant 15 minutes et la limitation du débit. **Le RSSI doit arbitrer si ces seuils conviennent**, ou s'il faut exiger 14 caractères ou plus, ou un contrôle contre une liste de mots de passe compromis.

### 4.5 Mots de passe temporaires

- Générés par `secrets.choice` (générateur cryptographique) : 14 caractères parmi 70 symboles, soit environ 85,8 bits.
- **Affichés une seule fois**, dans la réponse HTTP à l'administrateur, qui porte `Cache-Control: no-store`. Ils ne sont jamais stockés en clair : seule leur empreinte Argon2id est enregistrée. Ils ne sont jamais journalisés, ni conservés dans le stockage local du navigateur (ils restent dans l'état mémoire de la page d'administration).
- **Changement forcé** : un compte créé ou réinitialisé par un administrateur porte `must_change_password = 1`. Tant que l'utilisateur n'a pas choisi son propre mot de passe (`POST /auth/change-password`, qui exige le mot de passe actuel), toutes les routes, sauf `/auth/me`, `/auth/logout` et `/auth/change-password`, répondent `403 password_change_required`. Le frontend redirige vers la page `/change-password`.
- Une réinitialisation révoque toutes les sessions du compte. Un changement de mot de passe révoque toutes les autres sessions du compte.

## 5. Pourquoi ce hachage est irréversible, et ce que cela implique

Une fonction de hachage n'est pas un chiffrement : il n'existe **aucune clé** qui permette de revenir au mot de passe. La seule opération possible consiste à recalculer l'empreinte d'un mot de passe **candidat**, avec le sel et les paramètres enregistrés, puis à la comparer à l'empreinte stockée. Retrouver un mot de passe à partir de son empreinte revient donc à essayer des candidats un par un. Argon2id rend chaque essai coûteux en temps et en mémoire, et le sel unique empêche de mutualiser ces essais entre comptes (pas de tables précalculées, et deux comptes au même mot de passe ont des empreintes différentes).

Conséquences :

- **Aucune récupération n'est possible**, par personne : administrateur, DSI, éditeur ou hébergeur. La procédure « mot de passe oublié » est une **réinitialisation par un administrateur** (`POST /admin/users/{id}/reset-password`), tracée dans le journal d'audit (`admin_password_reset`).
- Si les paramètres étaient un jour jugés insuffisants, il est impossible de recalculer les empreintes existantes hors ligne. Elles sont mises à jour à la connexion suivante de chaque utilisateur (§ 4.3), et les comptes inactifs peuvent être réinitialisés.
- Le mot de passe DSI de Streamlit obéit à la même règle : un mot de passe DSI perdu se remplace en relançant `scripts/set_dsi_password.py`.

## 6. Scénarios de menace

| Scénario | Mesure en place | Risque résiduel |
|---|---|---|
| **Vol de la base** (`data/mispl.db`, sauvegarde, image Docker) | Seules des empreintes Argon2id salées sont stockées. L'image Docker exclut désormais `data/` et `.env` (`.dockerignore`). | La base n'est pas chiffrée au repos (SQLite) : emails, conversations et jetons de session sont lisibles (voir le rapport d'audit, section base de données). |
| **Attaque hors ligne** sur les empreintes volées | 64 Mio et 3 passes par essai, sel unique par compte : pas de table précalculée, pas de mutualisation. | Un mot de passe faible (déjà diffusé, par exemple) reste trouvable par dictionnaire, quel que soit l'algorithme. D'où la politique du § 4.4. |
| **Force brute en ligne** | Verrouillage du compte après 5 échecs pendant 15 minutes. Limites de 10 tentatives par couple (IP, compte) et de 30 par IP sur 5 minutes. Un mauvais mot de passe actuel lors d'un changement compte comme un échec. | Les compteurs de limitation sont en mémoire, propres à un processus, et remis à zéro au redémarrage. Derrière un proxy inverse, toutes les requêtes partagent la même IP (voir l'audit). |
| **Rejeu** (réutilisation d'une session ou d'un mot de passe intercepté) | Session aléatoire de 256 bits, cookie `HttpOnly`, `Secure` (par défaut), `SameSite=Strict`, expiration glissante de 8 h, révocable côté serveur. Réinitialisation et changement de mot de passe révoquent les autres sessions. Le changement de mot de passe exige le mot de passe actuel. | Le HTTPS de bout en bout relève du déploiement : le cookie `Secure` peut être désactivé par `MISPL_COOKIE_SECURE=false`. Les jetons de session sont stockés en clair en base (voir l'audit). |
| **Énumération de comptes** | Même code HTTP (401) et même message pour un email inconnu, un compte inactif, un mauvais mot de passe ou un compte verrouillé. | Aucun connu sur la connexion. La création d'un compte par un administrateur répond 409 si l'email existe, mais cette route est réservée aux administrateurs. |
| **Attaque temporelle** | Comparaison finale à temps constant dans l'implémentation Argon2. Pour un email inconnu, un compte inactif ou **un compte verrouillé** (ajouté le 2026-09-24), un calcul Argon2 factice rend la durée de réponse indiscernable d'un mauvais mot de passe. Pour le format PBKDF2 hérité du mot de passe DSI, la comparaison passe par `hmac.compare_digest`. | Une connexion réussie suivie d'un re-hachage prend environ deux fois plus longtemps, une seule fois par compte : cela ne révèle rien d'exploitable. |
| **Fuite par les journaux ou les réponses** | Les erreurs 422 ne renvoient plus la valeur soumise (champ `input` retiré). Le journal d'audit ne contient ni mot de passe, ni empreinte, ni jeton. Réponses de l'API en `Cache-Control: no-store`. Clé OpenRouter plus jamais envoyée au navigateur par Streamlit. | Un utilisateur qui collerait un mot de passe dans une question de chat le verrait conservé comme n'importe quelle question (le filtre DLP ne détecte pas les secrets) : voir l'audit. |

## 7. Tests de preuve exécutés

Commande : `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` (suite complète verte, voir le résultat en fin de rapport d'audit).

| Propriété démontrée | Test |
|---|---|
| Variante Argon2id, `v=19`, `m=65536,t=3,p=4`, sel de 16 octets, empreinte de 32 octets | `tests/api/test_password_lifecycle.py::TestArgon2Parameters::test_hash_is_argon2id_with_pinned_parameters` |
| Paramètres supérieurs ou égaux au minimum de l'OWASP | `…::TestArgon2Parameters::test_parameters_meet_owasp_minimum` |
| Même mot de passe, empreintes différentes (sel) | `tests/api/test_security.py::TestPasswordHashing::test_same_password_different_hash_each_time` |
| Empreinte faible re-hachée à la connexion ; pas de re-hachage en cas d'échec | `…::TestTransparentRehash` |
| Compte verrouillé : le calcul Argon2 est bien effectué (égalisation temporelle) | `…::TestTransparentRehash::test_locked_account_still_pays_argon2_cost` |
| Mot de passe temporaire, puis nouveau mot de passe : **absents de toutes les colonnes de toutes les tables** | `…::TestForcedPasswordChange::test_temp_password_never_stored_in_clear`, `…::test_change_password_success` |
| Changement forcé (403 avant changement), révocation des autres sessions, verrouillage | `…::TestForcedPasswordChange` |
| Erreur 422 sans écho du mot de passe ; `Cache-Control: no-store` | `…::TestNoPasswordLeak` |
| Journal d'audit sans mot de passe ni jeton | `…::TestNoPasswordLeak::test_audit_trail_records_events_without_secrets` |
| Migration de schéma non destructive et idempotente | `…::TestSchemaUpgrade` (et contrôle manuel sur une **copie** de `data/mispl.db`) |
| DSI : Argon2id, compatibilité PBKDF2 avec avertissement, script `.env` (relecture par python-dotenv) | `tests/security/test_access_mode.py::TestPasswordHashing`, `::TestSetDsiPasswordScript` |
| Base réelle : le seul compte existant a une empreinte `argon2id`, `m=65536,t=3,p=4`, sel de 16 octets, empreinte de 32 octets | Inspection en lecture seule du 2026-09-24 (comptages et formats uniquement, aucune empreinte affichée) |

### Limites

- Les tests prouvent le **comportement du code**, pas la robustesse des mots de passe réellement choisis ni la sécurité du déploiement (TLS, droits sur les fichiers, sauvegardes).
- La mesure de 86 ms dépend du poste. Il faut la refaire sur le serveur cible : viser, à titre indicatif, entre 50 et 500 ms par calcul, et ajuster `m` ou `t` si besoin (re-hachage transparent, § 4.3).
- La liste de mots de passe triviaux est courte. Un contrôle contre une base de mots de passe compromis (Have I Been Pwned en k-anonymat, ou liste hors ligne) reste à arbitrer.
- Pas de second facteur. Selon la PGSSI-S et l'analyse de risque de l'établissement, le RSSI peut l'exiger, au moins pour les comptes administrateurs.
- Streamlit (`app.py`) n'a pas de comptes : le mot de passe DSI y est partagé et aucune limite de tentatives n'est propre à cette interface (voir l'audit).

## 8. Décisions attendues du RSSI

1. Valider les paramètres Argon2id (§ 4.1), ou demander un profil plus lourd après mesure sur le serveur cible.
2. Valider la politique de mot de passe (§ 4.4) au regard de la délibération CNIL 2022-100 : longueur minimale, liste de mots de passe compromis.
3. Décider d'un second facteur pour les administrateurs.
4. Valider la procédure « mot de passe oublié » : réinitialisation par un administrateur uniquement, tracée au journal d'audit.
