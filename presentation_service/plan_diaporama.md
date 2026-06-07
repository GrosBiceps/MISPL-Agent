# Plan Diaporama — Assistant IA GLIMS/MISPL
**Durée cible : 20–25 min | Public : biologistes, techniciens, internes**

---

## DIAPO 1 — Titre

**Titre :**
> "Et si GLIMS pouvait se programmer tout seul ?"
> _Un assistant IA pour le code MISPL — Preuve de concept_

**Bullets :**
- Florian Magne — Interne en biologie médicale
- Projet personnel développé dans le cadre du stage
- Présentation : ce qu'on a, ce que ça fait, ce que ça ne fait pas encore

**Visuel :** Logo GLIMS + icône "robot + code" + logo HF Spaces. Fond sobre.

**Notes orateur :**
> Le titre est volontairement provocateur — non, GLIMS ne se programme pas tout seul.
> Mais on peut mettre une IA en position d'assistante. C'est la nuance que je vais expliquer.
> Cette présentation dure 20 minutes. Je vais être direct sur ce qui marche et ce qui ne marche pas encore.

---

## DIAPO 2 — Le problème concret (1/2)

**Titre :** "MISPL : un langage qui concentre la valeur… et les goulots"

**Bullets :**
- GLIMS = SIL. MISPL = cerveau du paramétrage (règles de validation, automatisations, déclencheurs)
- Toute modification de GLIMS passe par du code MISPL
- Compétence rare : formation longue, documentation volumineuse (~4 500 fichiers HTML)
- Quelques personnes dans le service maîtrisent vraiment

**Visuel :** Schéma simple : `Biologiste → besoin → [MISPL → GLIMS]`. Mettre une horloge sur la flèche MISPL pour symboliser le délai.

**Notes orateur :**
> Pour ceux qui ne touchent pas au paramétrage : MISPL c'est le langage qui dit à GLIMS quoi faire dans des situations particulières.
> Par exemple : "si l'hémoglobine est < 8 g/dL, ajouter automatiquement une demande de réticulocytes". Ça, ça s'écrit en MISPL.
> Le problème : écrire ça prend du temps, nécessite de connaître la documentation, et les personnes qui savent faire sont peu nombreuses et sollicitées.

---

## DIAPO 3 — Le problème concret (2/2)

**Titre :** "Ce que ça coûte en réalité"

**Bullets :**
- Temps de recherche dans la doc : 30–60 min pour une fonction peu connue
- Erreurs de déploiement : impact potentiel direct sur flux patients
- Dépendance à quelques experts → goulot d'étranglement
- Mise à jour des scripts existants : souvent reportée faute de temps

**Visuel :** Iceberg : partie visible = "écrire le script", partie immergée = "trouver la bonne fonction, lire la doc, tester, valider, documenter".

**Notes orateur :**
> L'analogie que j'utilise : c'est comme si vous deviez écrire un courrier officiel mais que vous deviez d'abord passer 45 minutes dans le BOFiP pour trouver le bon article de loi à citer.
> Le code lui-même n'est pas le problème. C'est tout ce qui entoure : trouver la bonne fonction dans 4 500 pages de documentation, gérer les cas particuliers, éviter les pièges.

---

## DIAPO 4 — L'idée : un assistant, pas un remplaçant

**Titre :** "RAG : chercher dans la doc, répondre avec la doc"

**Bullets :**
- RAG = Retrieval-Augmented Generation
- En 3 mots : **chercher → contextualiser → générer**
- L'IA ne "sait" rien par cœur : elle lit la documentation officielle GLIMS en temps réel
- Chaque réponse est ancrée dans un fichier source citable
- Si ce n'est pas dans la doc → elle le dit

**Visuel :** Schéma 3 cases : `[Question utilisateur] → [Moteur de recherche doc GLIMS] → [LLM génère réponse sourcée]`

**Notes orateur :**
> L'analogie : imaginez un assistant très méthodique qui, avant de vous répondre, va chercher dans la bibliothèque GLIMS, lit les pages pertinentes, et vous répond en citant ses sources.
> Il ne fabrique pas de réponses de mémoire. C'est ça la différence fondamentale avec ChatGPT de base.
> Si la fonction n'est pas dans la documentation — il dit "je ne sais pas, à vérifier dans GLIMS".

---

## DIAPO 5 — Architecture : ce qu'il y a sous le capot

**Titre :** "Comment ça marche concrètement"

**Bullets :**
- **Base documentaire :** 12 400 extraits indexés depuis la doc officielle GLIMS (HTML)
- **Recherche hybride :** BM25 (mots exacts) + vecteurs sémantiques → meilleur rappel
- **LLM :** modèle distant via API (OpenRouter) — aucun modèle local pour l'instant
- **Embeddings locaux :** aucune donnée ne part en dehors pour l'indexation
- **Linter intégré :** analyse statique avant affichage

**Visuel :** Pipeline horizontal : `Doc GLIMS → Indexation → [BM25 + Vecteurs] → LLM → Réponse sourcée + Linter`

**Notes orateur :**
> Pas besoin de retenir les termes techniques. Le message important : la documentation GLIMS est découpée en ~12 000 petits extraits, indexés par deux systèmes de recherche complémentaires.
> Quand vous posez une question, le système trouve les 6 extraits les plus pertinents et les donne au LLM pour qu'il construise une réponse. Le LLM n'invente pas — il résume ce qu'il a trouvé.
> Les embeddings (l'indexation) tournent en local. Seule la génération finale passe par une API externe — et uniquement votre question + des extraits de doc technique, jamais de données patient.

---

## DIAPO 6 — Démonstration (live ou screenshots)

**Titre :** "En pratique : 3 exemples réels"

**Bullets :**
- Ex. 1 : *"Ajouter réticulocytes si HB < 8 g/dL"* → script complet en 8 secondes
- Ex. 2 : *"Comment utiliser Order.AddRequest ?"* → documentation + exemple sourcé
- Ex. 3 : *"IPP: 1234567 comment valider..."* → bloqué automatiquement (DLP)

**Visuel :** Captures d'écran de l'interface Streamlit OU démo live si réseau OK.

**Notes orateur :**
> Je vais vous montrer 3 cas concrets.
> Le premier : un cas de reflex testing classique. Je tape ma demande en français, le système génère le script MISPL, cite ses sources, et indique son niveau de certitude.
> Le deuxième : une question de documentation pure — "comment fonctionne telle fonction ?"
> Le troisième : je glisse volontairement un faux IPP dans le prompt. Le système le détecte et bloque l'envoi. C'est le filtre DLP que j'ai intégré comme protection.
> [Si démo live :] Gardez en tête que la latence est de 4 à 16 secondes — on est sur le tier gratuit. En production ce serait plus rapide.

---

## DIAPO 7 — Ce que l'outil sait faire

**Titre :** "Capacités actuelles — ce qui est validé"

**Bullets :**
- ✅ Génération de scripts MISPL (reflex testing, validation, déclencheurs)
- ✅ Explication de fonctions MISPL documentées (~593 fonctions indexées)
- ✅ Navigation ERD GLIMS (Order → Specimen → Result → Action)
- ✅ Linter : boucles infinies, divisions entières, RETURN manquant, IF/ENDIF déséquilibré
- ✅ Blocage automatique des données sensibles (IPP, NIR, NIR belge)
- ✅ Réponse "je ne sais pas" quand la fonction n'est pas dans la doc

**Visuel :** Tableau checkboxes vert/orange/rouge.

**Notes orateur :**
> Ce que je viens de vous montrer n'est pas une démonstration taillée pour impressionner. Ce sont des cas testés, re-testés, et dont j'ai analysé les réponses une par une.
> La règle d'or que j'ai appliquée : si la fonction n'est pas dans la documentation, l'outil doit le dire explicitement — pas inventer un pseudo-code plausible.
> Les 593 fonctions indexées couvrent l'essentiel du MISPL quotidien. Il en manque, on le verra.

---

## DIAPO 8 — Transparence sur les limites

**Titre :** "Ce qui ne marche pas encore — et pourquoi c'est normal"

**Bullets :**
- ❌ Mémoire conversationnelle : chaque question repart de zéro
- ⚠️ Couverture doc : tables avancées (génétique, modules spéciaux) absentes
- ⚠️ Navigation ERD complexe : parfois la chaîne `.Action().Order().Result()` est approchée
- ⚠️ Latence : 4–16 s sur tier gratuit — acceptable en phase POC
- ❌ Pas encore de benchmark reproductible — évaluation qualitative seulement

**Visuel :** Même tableau que diapo 7 avec les croix/triangles.

**Notes orateur :**
> Je préfère vous dire maintenant ce qui ne marche pas bien plutôt que de vous laisser le découvrir après.
> La limite la plus gênante pour l'usage quotidien : pas de mémoire. Si vous avez une conversation en plusieurs échanges, l'outil ne se souvient pas de ce qui a été dit avant. Il faut re-contextualiser à chaque fois.
> La limite technique principale : certaines parties de la documentation GLIMS n'ont pas encore été indexées. Le travail de curation est continu.

---

## DIAPO 9 — Les risques — sans détour

**Titre :** "Les 4 risques que j'ai identifiés — et comment on les adresse"

**Bullets :**
- 🔴 R1 : **Code défectueux en prod** → pipeline 4 niveaux obligatoire (linter + sources + revue humaine + pré-prod)
- 🔴 R3 : **Pollution base RAG** → doc officielle uniquement, jamais de scripts "maison"
- 🟠 R2 : **Hallucination** → indicateur certitude + "je ne sais pas" si absent de la doc
- 🟡 R5 : **Données patients** → filtre DLP intégré + formation utilisateurs

**Visuel :** Matrice 2×2 probabilité/impact avec les 4 risques positionnés.

**Notes orateur :**
> Je vais être direct : le risque numéro 1, c'est qu'un script mal généré soit déployé en production GLIMS et perturbe le flux patient. C'est le scénario catastrophe.
> C'est pourquoi l'outil ne déploie rien lui-même. Il génère, il explique, il alerte — mais le déploiement reste entre les mains d'une personne habilitée, après validation explicite en pré-prod.
> Pour la RGPD : le filtre bloque automatiquement les IPP et numéros de sécurité sociale. Mais il faut aussi une culture du service : on ne met pas de données patients dans les prompts, point.

---

## DIAPO 10 — Le pipeline de validation

**Titre :** "L'assistant propose — le biologiste valide"

**Bullets :**
1. **Linter automatique** : erreurs syntaxiques et logiques avant affichage
2. **Sources citées** : chaque réponse pointe vers le fichier `.htm` source
3. **Revue humaine** : biologiste ou technicien référent obligatoire
4. **Test pré-production** : déploiement toujours en recette d'abord

**Visuel :** Diagramme de flux linéaire : `Génération → Linter → Affichage sourcé → Revue humaine → Pré-prod → Production`

**Notes orateur :**
> Ce pipeline n'est pas une contrainte bureaucratique — c'est ce qui rend l'outil utilisable en sécurité.
> Analogie : un interne rédige une ordonnance, le sénior valide avant signature. L'IA est l'interne. Vous êtes le sénior.
> Tant que ce principe est respecté, le risque R1 est très largement mitigé. C'est négociable ni pour moi ni pour le service.

---

## DIAPO 11 — Analyse économique rapide

**Titre :** "Combien ça coûte — vraiment"

**Bullets :**
- API LLM production : **< 100 €/mois** (selon volume)
- Curation documentaire : **5 à 15 j/h expert** — coût dominant
- Hébergement interne (GPU) : 10–15 k€ — **non justifié au lancement**
- Hébergement actuel (HF Spaces) : **gratuit** en POC
- ROI potentiel : 1 h/semaine économisée × équipe → rentabilisé en quelques mois

**Visuel :** Camembert ou barre : répartition des coûts. Mettre en évidence "curation = coût humain".

**Notes orateur :**
> Le coût technique est marginal. Le vrai investissement, c'est du temps humain pour s'assurer que la base documentaire est correcte et exhaustive.
> C'est pourquoi j'ai besoin de vous — pas pour coder, mais pour valider que ce que l'outil produit correspond à ce que vous attendez sur vos cas d'usage réels.

---

## DIAPO 12 — Feuille de route

**Titre :** "Les 3 phases : de la POC au service"

**Bullets :**
- **Phase 1 (M1–M2)** : LLM en prod payant, curation doc, pilote 2–3 utilisateurs référents
- **Phase 2 (M3–M8)** : retours terrain, 100–200 paires Q/R validées, linter étendu
- **Phase 3 (M9–M12)** : évaluation fine-tuning (si > 500 paires) + hébergement interne (si contrainte réglementaire)

**Visuel :** Timeline horizontale avec jalons. Flèche conditionnelle sur Phase 3 ("si conditions réunies").

**Notes orateur :**
> Je ne vends pas de fine-tuning ni d'hébergement interne pour l'instant. Ces options sont conditionnelles.
> Le fine-tuning n'est pertinent que si on a suffisamment de données validées. L'hébergement interne n'est pertinent que si le volume ou la réglementation l'exige.
> La priorité immédiate : passer en conditions réelles avec 2 ou 3 utilisateurs référents qui testent sur leurs cas d'usage quotidiens et me font remonter les erreurs.

---

## DIAPO 13 — Ce dont j'ai besoin de vous

**Titre :** "Comment participer — 3 rôles concrets"

**Bullets :**
- 👤 **Pilote utilisateur** : tester l'outil sur vos vrais besoins MISPL, remonter les erreurs
- 📋 **Validateur de contenu** : vérifier que les réponses générées sont cliniquement correctes
- 🗂️ **Curateur** : identifier des scripts MISPL existants de qualité à intégrer comme référence

**Visuel :** 3 icônes / 3 colonnes. Pas de tableau surchargé.

**Notes orateur :**
> Je ne vous demande pas de coder. Je vous demande d'utiliser l'outil comme vous le feriez naturellement et de me dire quand la réponse est mauvaise, approximative, ou manquante.
> Chaque retour terrain est de l'or pour améliorer le système. Le feedback humain est la ressource la plus précieuse dans ce type de projet.
> Si 2 ou 3 personnes dans cette salle veulent être pilotes, je les contacte cette semaine pour leur donner accès et définir une procédure de feedback simple.

---

## DIAPO 14 — Vision long terme

**Titre :** "Où on peut aller — si le pilote est concluant"

**Bullets :**
- Interface intégrée dans GLIMS (zéro rupture de contexte)
- Benchmark reproductible pour mesurer objectivement les performances
- Partage avec d'autres labos utilisant GLIMS (communauté utilisateurs)
- Potentiellement : formation accélérée des nouveaux internes/techniciens via l'outil

**Visuel :** Roadmap visuelle avec horizon 1 an / 3 ans. Garder sobre.

**Notes orateur :**
> Ces pistes ne sont pas des promesses — ce sont des directions. La prochaine étape concrète, c'est le pilote.
> Si dans 6 mois, 2 techniciens référents économisent chacun 30 minutes par semaine sur le paramétrage MISPL, c'est déjà une réussite.

---

## DIAPO 15 — Conclusion

**Titre :** "En résumé : un assistant, pas un oracle"

**Bullets :**
- L'IA propose du code MISPL fondé sur la documentation officielle
- Le biologiste et le technicien restent décisionnaires et responsables
- Preuve de concept fonctionnelle, limitations identifiées et documentées
- Prochaine étape : pilote terrain avec 2–3 volontaires

**Visuel :** Slide épuré. Une phrase centrale : _"L'assistant propose. Vous validez."_

**Notes orateur :**
> Je vais conclure par ce que j'espère que vous retenez de cette présentation.
> Ce n'est pas "l'IA va remplacer les techniciens en paramétrage". C'est "il existe maintenant un outil qui peut réduire significativement le temps passé à chercher dans la documentation et à écrire les premières versions de scripts".
> La valeur de cet outil dépend directement de votre implication pour le tester et le corriger. Merci pour votre attention. Je suis disponible pour les questions.

---

## DIAPO 16 (optionnelle) — Questions / Discussion

**Titre :** "Questions"

**Visuel :** QR code vers l'interface HF Spaces + adresse mail de contact.

---

## ANNEXES (non présentées, disponibles si questions)

### A1 — Stack technique complète
- SentenceTransformer `paraphrase-multilingual-MiniLM-L12-v2` (384 dims)
- ChromaDB vectorstore persistant
- BM25Okapi (rank_bm25)
- RRF k=25, fetch_n=36
- OpenRouter API (nemotron-3-super-120b comme modèle par défaut)
- Streamlit 1.x, Docker, Hugging Face Spaces

### A2 — Audit réglementaire résumé
- RGPD : usage nominal hors champ (aucune donnée patient dans la base RAG)
- HDS : non requis en conditions nominales
- ISO 15189 §6.6 : validation de chaque script obligatoire avant prod
- MDR : non qualifié comme DM (pas de finalité diagnostique)

### A3 — Exemple de réponse complète (capture d'écran annotée)

---

## TIMING SUGGÉRÉ

| Diapo | Contenu | Durée |
|---|---|---|
| 1–3 | Contexte + problème | 4 min |
| 4–5 | RAG + architecture | 3 min |
| 6 | **Démo live** | 5 min |
| 7–9 | Capacités + limites + risques | 4 min |
| 10–11 | Pipeline + coûts | 2 min |
| 12–13 | Roadmap + appel à participation | 3 min |
| 14–15 | Vision + conclusion | 2 min |
| Questions | — | 5 min |
| **Total** | | **~28 min** |

> Conseil : si besoin de réduire à 20 min, couper diapo 11 (coûts) et condenser 12+13 en une seule slide.
