# Règle : Anti-Hallucination MISPL

## Règle
Ne JAMAIS générer une fonction MISPL sans source documentaire confirmée dans le RAG.

## Pourquoi
MISPL est un langage propriétaire fermé. Les fonctions inventées seront rejetées par GLIMS avec une erreur de compilation silencieuse ou pire, un comportement inattendu sur les résultats patients. Dans un contexte de laboratoire clinique, une erreur de script peut impacter directement la prise en charge d'un patient.

## Comment appliquer
1. Avant d'utiliser une fonction dans le code généré → vérifier sa présence dans le contexte RAG
2. Si absente → écrire un commentaire `// Fonction non trouvée dans la documentation` et proposer du pseudo-code
3. Si partielle (signature incomplète) → qualifier ⚠️ Probable et recommander un test dans l'environnement de développement GLIMS
4. Toujours inclure la source dans la réponse : `Source : function_string.htm — section "Substr"`

## Exemple de réponse correcte si fonction absente
```
🔬 À vérifier dans GLIMS

La fonction `GetWorkList()` n'apparaît pas dans les extraits documentaires disponibles.

Voici du pseudo-code structuré basé sur les patterns MISPL connus :
// À VÉRIFIER dans l'éditeur MISPL GLIMS avant déploiement
STRING PROGRAM
  // GetWorkList() — syntaxe exacte à confirmer
  STRING wl;
  wl := GetWorkList(.WorkListId);  // Paramètres à vérifier
RETURN wl;
```
