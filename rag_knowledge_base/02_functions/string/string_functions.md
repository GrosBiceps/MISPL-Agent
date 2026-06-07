---
id: "functions_string"
type: "fonction_core"
domaine: "manipulation_chaines"
langage_proxy: "Progress ABL / OpenEdge"
context: ["all"]
table_abbrev: null
return_type: "String | Integer | Logical"
priority: "high"
keywords_fr: ["extraire", "caractères", "premiers caractères", "longueur", "chercher", "remplacer", "majuscule", "minuscule", "découper", "liste", "délimiteur", "position", "sous-chaîne", "tronquer", "rembourrer"]
anti_hallucination: ["Left n'existe pas → Substr", "Length n'existe pas → Len", "UCase n'existe pas → ToUpper", "LCase n'existe pas → ToLower", "Mid n'existe pas → Substr", "InStr n'existe pas → Index"]
tags: [string, substr, Substr, len, Len, index, Index, replace, Replace, trim, Trim, Ltrim, Rtrim, upper, ToUpper, lower, ToLower, chr, Chr, entry, Entry, NumEntries, Fill, Lookup, Matches, Cpad, Lpad, Rpad, Sort, Strip]
---

# Fonctions de manipulation de chaînes de caractères

Équivalent ABL : module `string.i` et fonctions natives CHARACTER.

---

## Chr
**Signature** : `String Chr(Integer OrdinalNumber)`  
Convertit un code ordinal (0–255) en le caractère correspondant dans le jeu de caractères actif. Retourne `?` hors plage.  
**Équivalent ABL** : `CHR(n)`

```mispl
Return Chr(65);   /* retourne "A" */
Return Chr(27);   /* retourne le caractère ESCAPE */
```

---

## Cpad
**Signature** : `String Cpad(String s, Integer l, String f)`  
Génère une chaîne de longueur `l` en centrant `s` et en remplissant les bords avec `f`.  
```mispl
RETURN Cpad("abc", 10, "-");  /* retourne "----abc---" */
```

---

## Entry
**Signature** : `String Entry(Integer Position, String List, String Delimiter)`  
Extrait l'élément à la position `Position` dans une liste délimitée par `Delimiter` (défaut: virgule).  
`Position` hors plage → retourne `?`. Délimiteur vide/inconnu → virgule par défaut.  
**Équivalent ABL** : `ENTRY(n, list, delim)`

```mispl
/* Extraire le 2ème élément d'une liste CSV */
STRING elem;
elem := Entry(2, "Hb,Ht,MCV,MCHC", ",");   /* retourne "Ht" */

/* Itération sur liste avec NumEntries */
INTEGER i;
i := 1;
WHILE i <= NumEntries("B_PSA,B_PSAL,B_FPSA", ",") DO
  /* Entry(i, "B_PSA,B_PSAL,B_FPSA", ",") = mnémonique courant */
  i := i + 1;
DONE;
```

---

## ExtractTag
**Signature** : `String ExtractTag(String Tag, String List, String Delimiter)`  
Extrait la valeur associée à un tag dans une liste de paires `Tag=Valeur{Délimiteur...}`.  
Tags insensibles à la casse. Délimiteur par défaut : virgule.

```mispl
/* Lire une valeur taguée dans une chaîne paramétrique */
STRING bio;
bio := ExtractTag("Biologiste", "Biologiste=martin,Garde=oui,Service=BIOCHIMIE", ",");
/* retourne "martin" */
```

---

## Fill
**Signature** : `String Fill(String Source, Integer Repeats)`  
Concatène `Source` un nombre `Repeats` de fois. Si `Repeats <= 0`, retourne une chaîne vide.  
**Équivalent ABL** : `FILL(s, n)`

```mispl
STRING ligne;
ligne := Fill("=", 40);   /* retourne "========================================"  */
ligne := Fill("- ", 5);   /* retourne "- - - - - " */
```

---

## FitText
**Signature** : `String FitText(String InputString, Integer Maxlinelength, String FirstPrefix, String Prefix, String Suffix)`  
Coupe `InputString` en lignes de largeur maximale `Maxlinelength`, en préfixant chaque ligne par `Prefix` et suffixant par `Suffix`. La première ligne utilise `FirstPrefix` si fourni (sinon `Prefix`). Retourne `?` si `FirstPrefix` dépasse `Maxlinelength`.

```mispl
/* Formater un texte en colonne 60 chars avec marqueurs */
STRING result;
result := FitText("Texte long à formater en colonnes", 60, "[ Debut: ", "[   ", " ]");
```

---

## IfKnownString
**Signature** : `String IfKnownString(String Value)`  
Retourne `Value` inchangée si sa valeur est connue (non `?`), sinon retourne une chaîne vide `""`.  
**1 seul paramètre** — pas de paramètre Default (utiliser un IF explicite pour une valeur par défaut personnalisée).

```mispl
STRING val;
val := IfKnownString(.Result.Attribute("Value"));
/* Si .Result.Attribute("Value") = ? → val = "" */
/* Sinon → val = la valeur du résultat */

/* Pour une valeur par défaut personnalisée : */
IF .Result.Attribute("Value") <> ? THEN
  val := .Result.Attribute("Value");
ELSE
  val := "Non renseigné";
ENDIF;
```

---

## Index
**Signature** : `Integer Index(String Source, String Target)`  
Retourne la position (base 1) de la première occurrence de `Target` dans `Source`.  
Retourne `0` si absent. Retourne `1` si `Target` est une chaîne vide. Recherche insensible à la casse.  
**ATTENTION** : Nom exact `Index`, **pas** `InStr` (qui n'existe pas).  
**Équivalent ABL** : `INDEX(source, target)`

```mispl
/* Tester si une valeur contient "<" ou ">" (qualificatif) */
IF Index(.Result.Attribute("Value"), "<") > 0
  OR Index(.Result.Attribute("Value"), ">") > 0
THEN
  /* valeur qualifiée — ne pas traiter numériquement */
ENDIF;

/* Chercher un mnémonique dans une liste */
IF Index("B_PSA,B_PSAL,B_FPSA", .ResultMnemonic) > 0 THEN ...
```

---

## Len
**Signature** : `Integer Len(String Source)`  
Retourne le nombre de caractères de `Source`.  
**ATTENTION** : Le nom est `Len`, **pas** `Length` (qui n'existe pas en MISPL).  
**Équivalent ABL** : `LENGTH(s)`

```mispl
INTEGER taille;
taille := Len("Bonjour");   /* retourne 7 */
```

---

## Lookup
**Signature** : `Integer Lookup(String Entry, String List, String Delimiter)`  
Retourne la position (base 1) de `Entry` dans la liste `List`. Retourne `0` si absent.  
Différent de `Index` : `Lookup` cherche un **élément entier** de liste, `Index` cherche une **sous-chaîne**.  
**Équivalent ABL** : `LOOKUP(entry, list, delim)`

```mispl
/* Trouver la position d'un jour de semaine dans une liste ordonnée */
INTEGER posJour;
posJour := Lookup(DateTimeToString(Action.Order().ReceiptTime, "%a"),
                  "lun,mar,mer,jeu,ven,sam,dim", ",");
/* posJour = 1..7, ou 0 si non trouvé */

/* Tester si un mnémonique est dans une liste blanche */
IF Lookup("B_PSA", "B_PSA,B_PSAL,B_FPSA", ",") > 0 THEN ...
```

---

## Lpad
**Signature** : `String Lpad(String s, Integer l, String f)`  
Aligne `s` à droite dans un champ de largeur `l`, en remplissant à gauche avec `f`.

```mispl
Lpad("42", 6, "0")    /* retourne "000042" */
Lpad("abc", 8, " ")   /* retourne "     abc" */
```

---

## Ltrim / Rtrim / Trim
**Signatures** :
```
String Ltrim(String Source, String TrimChars)
String Rtrim(String Source, String TrimChars)
String Trim(String Source, String TrimChars)
```
Supprime les caractères `TrimChars` en début (Ltrim), fin (Rtrim) ou les deux (Trim).  
**Équivalent ABL** : `LEFT-TRIM()`, `RIGHT-TRIM()`, `TRIM()`

---

## Matches
**Signature** : `Logical Matches(String Source, String Pattern, Logical CaseSensitive)`  
Teste si `Source` correspond au motif regex `Pattern`. `CaseSensitive = NO` pour ignorer la casse.  
Syntaxe pattern : `.` = n'importe quel caractère, `[0-9]` = plage, `*` = zéro ou plusieurs chars. Caractères spéciaux `(`, `)` doivent être échappés avec `\`.

```mispl
/* Tester si un ID commence par 3 zéros */
IF Matches(.InternalId, "000....", NO) THEN ...

/* Tester résultat textuel négatif (insensible casse) */
IF Matches(.Result.Attribute("Value"), ".*[Nn][Ee][Gg].*", NO) THEN ...

/* Echapper les parenthèses */
IF Matches(valeur, "Neg \(z.*", NO) THEN ...
```

---

## PutTag
**Signature** : `String PutTag(String Tag, String StringValue, String List, String Delimiter)`  
Insère ou remplace l'entrée `Tag=StringValue` dans une liste de paires taguées. Tags insensibles à la casse, longueur max 64 chars. Inverse de `ExtractTag`.

```mispl
/* Construire/mettre à jour une liste de paramètres taguée */
STRING params;
params := "";
params := PutTag("Biologiste", "martin", params, ",");
params := PutTag("Service", "BIOCHIMIE", params, ",");
/* params = "Biologiste=martin,Service=BIOCHIMIE" */

/* Mettre à jour une valeur existante */
params := PutTag("Biologiste", "dupont", params, ",");
```

---

## RangeLabel
**Signature** : `String RangeLabel(Fractional TestValue, String RangeList)`  
Détermine dans quelle tranche numérique se trouve `TestValue` et retourne le label correspondant.  
`RangeList` format : `"<seuil1>:<label1>,<seuil2>:<label2>,..."`

```mispl
/* Classifier une durée de délai en tranches */
STRING tranche;
tranche := RangeLabel(StringToFractional(.Result.Attribute("Value")),
                      "0:Normal,60:Moyen,120:Long,240:Critique");
/* Si valeur = 180 → retourne "Long" */
```

---

## RemoveEntry
**Signature** : `String RemoveEntry(String List, String Delimiter, Integer Position, Integer Count)`  
Supprime `Count` éléments depuis la position `Position` (base 1) dans la liste délimitée.  
`Count < 0` ou trop grand → supprime jusqu'à la fin. `Position` hors liste → retourne liste inchangée.

```mispl
/* Supprimer les éléments 2 et 3 d'une liste */
STRING result;
result := RemoveEntry("abc,def,ghi,jkl,mno", ",", 2, 2);
/* retourne "abc,jkl,mno" */

/* Supprimer le dernier élément */
INTEGER n;
n := NumEntries(maListe, ",");
maListe := RemoveEntry(maListe, ",", n, 1);
```

---

## NumEntries
**Signature** : `Integer NumEntries(String List, String Delimiter)`  
Compte le nombre d'éléments dans une liste délimitée. Défaut délimiteur : virgule.  
**Équivalent ABL** : `NUM-ENTRIES(list, delim)`

---

## Ord
**Signature** : `Integer Ord(String Character)`  
Retourne le code ordinal du premier caractère de `Character`. Inverse de `Chr`.

---

## Replace
**Signature** : `String Replace(String Source, String From, String To)`  
Remplace toutes les occurrences de `From` par `To` dans `Source`.  
**Équivalent ABL** : `REPLACE(s, from, to)`

---

## Rpad
**Signature** : `String Rpad(String s, Integer l, String f)`  
Aligne `s` à gauche dans un champ de largeur `l`, en complétant à droite avec `f`.

---

## Sort
**Signature** : `String Sort(String List, String Delimiter)`  
Trie les entrées d'une liste délimitée par ordre alphabétique.

---

## Strip
**Signature** : `String Strip(String Source, String Type, String TrimChar)`  
`Type` : "L" (gauche), "R" (droite), "T" (les deux), "A" (tout, y compris intérieur).

---

## Substr
**Signature** : `String Substr(String Source, Integer StartPos, Integer Length)`  
Extrait `Length` caractères de `Source` à partir de la position `StartPos` (base 1).  
**ATTENTION** : Le nom est `Substr`, **pas** `Left`, `Right` ou `Mid` (qui n'existent pas).  
**Équivalent ABL** : `SUBSTRING(s, start, len)`

```mispl
/* Extraire le 1er caractère pour tester < ou > */
IF NOT (Substr(.Result.Attribute("Value"), 1, 1) = "<") THEN ...

/* Extraire les 3 premiers caractères */
STRING prefixe;
prefixe := Substr(maChaine, 1, 3);
```

---

## ToLower / ToUpper
**Signatures** :
```
String ToLower(String Source)
String ToUpper(String Source)
```
Conversion casse. **ATTENTION** : Noms exacts `ToLower`/`ToUpper`, **pas** `LCase`/`UCase`.  
**Équivalent ABL** : `LC()` / `CAPS()`

---

## Translate / TranslateCharacters
**Signatures** :
```
String Translate(String Source, String From, String To)
String TranslateCharacters(String Source, String From, String To)
```
Remplace caractère par caractère les occurrences de `From` par leurs correspondants dans `To`.

---

## XmlEscaped
**Signature** : `String XmlEscaped(String Source)`  
Échappe les caractères spéciaux XML (`<`, `>`, `&`, `"`) dans `Source`.

---

## Cas d'usage CHU — Substr pour filtrer valeurs avec qualificatif

```mispl
/* B_Ajout B_COM_VR_PAL : ignorer valeurs "<X" ou ">X" */
LOGICAL PROGRAM
  IF Action.Object.AgeInYears(Today()) <= 19
    AND .Result.Mantissa <> ?
    AND NOT (Substr(.Result.Attribute("Value"), 1, 1) = "<")
    AND NOT (Substr(.Result.Attribute("Value"), 1, 1) = ">")
  THEN
    Action.Order().AddRequest("B_COM_VR_PAL", ?, ?);
  ENDIF;
RETURN YES;
```
