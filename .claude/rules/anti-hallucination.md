# Règle : Anti-Hallucination MISPL

## Règle
Ne JAMAIS générer une fonction MISPL sans source documentaire confirmée dans le RAG.

## Pourquoi
MISPL est un langage propriétaire fermé. Les fonctions inventées seront rejetées par GLIMS avec une erreur de compilation silencieuse ou pire, un comportement inattendu sur les résultats patients. Dans un contexte de laboratoire clinique, une erreur de script peut impacter directement la prise en charge d'un patient.

## Comment appliquer
1. Avant d'utiliser une fonction dans le code généré → vérifier sa présence dans le contexte RAG
2. Si absente → l'indiquer (« Fonction non trouvée dans la documentation ») et proposer du pseudo-code qui N'APPELLE PAS la fonction absente : alternative à base de fonctions documentées, ou étapes décrites en commentaires `/* ... */`
3. Si partielle (signature incomplète) → qualifier ⚠️ Probable et recommander un test dans l'environnement de développement GLIMS
4. Toujours inclure la source dans la réponse : `Source : rag_knowledge_base/02_functions/string/string_functions.md — section "Substr"`
5. Commentaires MISPL : uniquement `/* ... */` (`//` n'est pas un commentaire MISPL)

## Exemple de réponse correcte si fonction absente
```
⚠️ Fonction non trouvée dans la documentation. Voici du pseudo-code structuré à vérifier dans GLIMS.

La fonction `GetWorkList()` n'apparaît pas dans les extraits documentaires disponibles :
elle n'est donc jamais appelée ci-dessous.

STRING PROGRAM
  STRING wl;
  /* À VÉRIFIER dans l'éditeur MISPL GLIMS : aucune fonction documentée ne renvoie */
  /* la liste de travail. Étape à réaliser : lire l'identifiant de la liste, puis  */
  /* utiliser la fonction adaptée une fois confirmée dans la documentation.        */
  wl := ?;
RETURN wl;
```
