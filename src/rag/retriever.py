"""
Retriever hybride GLIMS/MISPL — v2.
Failles corrigées vs v1 :
  - BM25 (rank_bm25) + dense ChromaDB → Reciprocal Rank Fusion
  - Exact-match boost : si la query contient un nom de fonction connu → score 1.0
  - Reorder anti-"Lost in the Middle" : meilleur chunk en #1, second en #last
  - Métadonnées enrichies remontées (function_name, signature, return_type)
  - Instance ChromaDB/BM25 créée une seule fois (singleton) pour éviter rechargements
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi


ROOT = Path(__file__).parent.parent.parent
VECTORSTORE_PATH = ROOT / "docs" / "chunks" / "vectorstore"
BM25_CORPUS_PATH = ROOT / "docs" / "chunks" / "bm25_corpus.json"
COLLECTION_NAME = "glims_mispl_docs"

# Coefficient RRF — k=25 optimisé corpus technique dense (k=60 dilue trop sur ~300 chunks pertinents)
RRF_K = 25

# Catégories considérées "MISPL pur" — boost score RRF +0.05
_MISPL_PURE_CATEGORIES = {
    "string", "datetime", "math", "conversion", "misc", "interactive",
    "error", "billing", "variables", "syntax", "order_table", "result_table",
    "specimen_table", "action_table", "specificsite_table", "nonconformity_table",
    "regex", "mail", "texts",
}


# ── Tokenisation simple pour BM25 (FR + EN + identifiants techniques) ─────────

def _normalize(text: str) -> str:
    """Supprimer les accents pour matching cross-langue (chaîne → chaine)."""
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode()


# Stemmer français — initialisé une seule fois (lazy, thread-safe)
_FR_STEMMER = None

def _get_stemmer():
    """Charge SnowballStemmer("french") une seule fois depuis NLTK (absent → désactivé)."""
    global _FR_STEMMER
    if _FR_STEMMER is None:
        try:
            from nltk.stem import SnowballStemmer
            _FR_STEMMER = SnowballStemmer("french")
        except ImportError:
            _FR_STEMMER = False
    return _FR_STEMMER if _FR_STEMMER is not False else None


def _is_fr_word(word: str) -> bool:
    """Mot FR pur : alpha, lowercase, len>=4. Protège les identifiants MISPL du stemmer."""
    return len(word) >= 4 and word.isalpha() and word == word.lower() and not re.search(r"[0-9]", word)


def _tokenize(text: str) -> list[str]:
    """
    Tokenise pour BM25 : préserve PascalCase + dé-accentue + stemming FR sélectif.
    'GetSiteAttribute' → ['getsiteattribute', 'get', 'site', 'attribute']
    'ajouter' → ['ajouter', 'ajout']  (stemmé)
    'chaîne' → ['chaine', 'chaine']  (dé-accentué)
    Les identifiants MISPL (PascalCase) ne sont PAS stemmés.
    """
    stemmer = _get_stemmer()
    tokens = []
    for word in re.findall(r"[A-Za-z0-9À-ɏ_\-]+", text):
        lower = word.lower()
        ascii_lower = _normalize(lower)
        tokens.append(lower)
        if ascii_lower != lower:
            tokens.append(ascii_lower)  # version sans accent
        # Découper PascalCase : 'GetSiteAttribute' → 'get', 'site', 'attribute'
        parts = re.findall(r"[A-Z][a-z0-9]+|[a-zÀ-ɏ]+|[0-9]+", word)
        if len(parts) > 1:
            for p in parts:
                pl = p.lower()
                tokens.append(pl)
                tokens.append(_normalize(pl))
                if stemmer and _is_fr_word(pl):
                    st = stemmer.stem(pl)
                    if st != pl:
                        tokens.append(st)
        elif stemmer and _is_fr_word(ascii_lower):
            st = stemmer.stem(ascii_lower)
            if st != ascii_lower:
                tokens.append(st)
    return tokens


# Synonymes FR/EN pour les fonctions MISPL les plus courantes
# Permet au BM25 de retrouver la bonne fonction depuis une question en français
_FN_SYNONYMS: dict[str, list[str]] = {
    "Substr":              ["extraire sous-chaine substring partie chaine caracteres portion"],
    "Len":                 ["longueur longueur longueur taille chaine length len nombre caracteres"],
    "Index":               ["position trouver chercher chaine indexOf find"],
    "Replace":             ["remplacer substituer remplacement replace"],
    "Ltrim":               ["supprimer espaces gauche trim"],
    "Rtrim":               ["supprimer espaces droite trim"],
    "Trim":                ["supprimer espaces trim"],
    "ToUpper":             ["majuscule uppercase convertir"],
    "ToLower":             ["minuscule lowercase convertir"],
    "Chr":                 ["caractere ascii code ordinal"],
    "Ord":                 ["code ordinal ascii caractere"],
    "Today":               ["date aujourd hui jour courant current date"],
    "Now":                 ["heure maintenant time current"],
    "DateToString":        ["formater date afficher format date chaine"],
    "DateTimeToString":    ["formater datetime format afficher"],
    "StringToDate":        ["convertir chaine date parse"],
    "DateDiffInYears":     ["difference annees age calcul"],
    "IntegerToString":     ["convertir entier chaine texte nombre to string"],
    "FractionalToString":  ["convertir decimal fraction chaine formater nombre"],
    "StringToInteger":     ["convertir chaine entier parse int"],
    "StringToFractional":  ["convertir chaine decimal float parse"],
    "ToString":            ["convertir vers chaine texte"],
    "Round":               ["arrondir arrondi decimal"],
    "Truncate":            ["tronquer truncate decimal"],
    "Abs":                 ["valeur absolue positif"],
    "Sqrt":                ["racine carree square root"],
    "Exp":                 ["puissance exposant power"],
    "Log":                 ["logarithme"],
    "CurrentUser":         ["CurrentUser CurrentUser utilisateur utilisateur utilisateur connecte login nom user courant"],
    "CurrentDepartment":   ["departement discipline service courant"],
    "CurrentRole":         ["role utilisateur connecte"],
    "CurrentTerminal":     ["terminal poste station courant"],
    "AddLogEntry":         ["AddLogEntry AddLogEntry journal journal journal log log audit audit trace ecrire entree historique"],
    "GetSiteAttribute":    ["attribut site lire parametre configuration global"],
    "SetSiteAttribute":    ["attribut site ecrire modifier parametre configuration global"],
    "NextValue":           ["prochain increment sequence compteur auto"],
    "DatedIdentifier":     ["identifiant date sequence numero"],
    "Identifier":          ["identifiant sequence numero"],
    "IsHoliday":           ["jour ferie vacances conge calendrier"],
    "SendMail":            ["envoyer email mail courriel"],
    "Translate":           ["traduire traduction langue translation"],
    "NumEntries":          ["nombre entrees compter liste delimiter"],
    "Entry":               ["element entree liste position delimiter"],
    "Sort":                ["trier ordre alphabetique sort"],
    "Matches":             ["correspondre regex pattern match expression reguliere"],
    "XmlEscaped":          ["echapper xml escape caracteres speciaux"],
    "PeekDate":            ["lire variable partagee date shared"],
    "PeekInteger":         ["lire variable partagee entier shared"],
    "PeekDecimal":         ["lire variable partagee decimal shared"],
    "PeekLogical":         ["lire variable partagee logique logical shared"],
    "PeekRecId":           ["lire variable partagee recid id shared"],
    "PokeDate":            ["ecrire variable partagee date shared"],
    "PokeInteger":         ["ecrire variable partagee entier shared"],
    "PokeDecimal":         ["ecrire variable partagee decimal shared"],
    "PokeLogical":         ["ecrire variable partagee logique logical shared"],
    "PokeRecId":           ["ecrire variable partagee recid id shared"],
    "AskYesNo":            ["demander oui non dialogue confirmation interactif"],
    "AskString":           ["demander texte saisie dialogue interactif"],
    "Message":             ["afficher message dialogue popup"],
    # Noms réels dans la doc (PeekCharacter/PokeCharacter — pas PeekString/PokeString)
    "PeekCharacter":       ["lire variable partagee chaine shared string peek"],
    "PokeCharacter":       ["ecrire variable partagee chaine shared string poke"],
    # Fonctions table-spécifiques Order
    "OrderAttribute":      ["order attribute attribut dossier liste analyses materiels specimens proprietes RequestList PropertyList MaterialList SpecimenList Summary StationCodeList"],
    "OrderGetIdentifier":  ["order identifier identifiant dossier get"],
    "OrderRecalculateSpecimen": ["order recalculer specimen interne id"],
    # Fonctions table-spécifiques Result
    "ResultAttribute":     ["result attribute valeur resultat Value ExpandedValue ReferenceValue ReagentUsage EncounterInfo format BrowseFormat ReportFormat"],
    "ResultWorkSpecimen":  ["result workspecimen echantillon travail specimen mesure"],
    # Fonctions table-spécifiques Specimen
    "SpecimenAttribute":   ["specimen attribute attribut echantillon PropertyList MaterialList SamplingTime RootInternalId Urgency StorageList"],
    "SpecimenAddRequest":  ["specimen add request ajouter demande analyse echantillon"],
    "SpecimenCollectionInfo": ["specimen collection info prelevement ContainerCount"],
    "SpecimenDirectParent": ["specimen parent direct echantillon parent derive"],
    "SpecimenResult":      ["specimen result resultat analyse echantillon"],
    "SpecimenSetMeasuredSize": ["specimen set measured size volume quantite mesuree"],
    # SendMail variantes table-spécifiques
    "CorrespondentSendMail":["correspondent sendmail envoyer mail correspondant externe email"],
    "UserSendMail":         ["user sendmail envoyer mail utilisateur interne sc_user"],
    "RoleSendMail":         ["role sendmail envoyer mail role tous utilisateurs sc_role"],
    # Matches() utilise regex MISPL
    "Matches":              ["matches regex expression reguliere pattern correspondance test chaine"],
    # Nouvelles fonctions Order (ord.htm)
    "OrderAddRequest":      ["order addrequest ajouter demandes dossier analyses liste requestlist"],
    "OrderGetSpecimen":     ["order getspecimen iterer parcourir echantillons dossier boucle"],
    "OrderResult":          ["order result recuperer resultat dossier analyse PropertyMnemonic"],
    "OrderIsRequested":     ["order isrequested verifier demande analyse contient dossier"],
    "OrderPropertyList":    ["order propertylist liste analyses resultats statut classification"],
    "OrderSummary":         ["order summary resume dossier journal nominatif compact outline"],
    "OrderCancelResults":   ["order cancelresults annuler discontinuer resultats dossier"],
    "OrderHasMissingSpecimens": ["order hasmissingspecimens echantillons manquants"],
    "OrderIsEmpty":         ["order isempty vide dossier sans demande"],
    "OrderCreateReport":    ["order createreport creer planifier compte-rendu cr mispl"],
    "OrderCreateMediumReport": ["order createmediumreport rapport fax email courrier medium"],
    "OrderAddOrderTodoItem":["order addordertodoitem tache todo liste"],
    "OrderGetDiagnosis":    ["order getdiagnosis diagnostic code parcourir"],
    "OrderToBePhoned":      ["order tobephoned telephoner marquer appel"],
    "OrderCheckFSE":        ["order checkfse feuille soins electronique france erreur"],
    "OrderReportList":      ["order reportlist liste comptes-rendus scope template"],
    "OrderBudgetInvoice":   ["order budgetinvoice facture budget classe"],
    "OrderInvoiceItemsData":["order invoiceitemsdata elements facture montant nomenclature"],
    # Nouvelles fonctions Specimen (spmn.htm)
    "SpecimenAddCarriers":  ["specimen addcarriers plaques microbiologie milieu ensemencement"],
    "SpecimenAddBlocks":    ["specimen addblocks blocs pathologie"],
    "SpecimenCarrierCount": ["specimen carriercount compter plaques milieu"],
    "SpecimenIsolationCount":["specimen isolationcount compter isolements microbiologie organisme"],
    "SpecimenFirstRequest": ["specimen firstrequest premiere demande ancienne requete order"],
    "SpecimenLastRequest":  ["specimen lastrequest derniere demande recente requete order"],
    "SpecimenGetStorage":   ["specimen getstorage stockage serotheque position portoir"],
    "SpecimenSetStorage":   ["specimen setstorage attribuer position stockage serotheque"],
    "SpecimenTariffResult": ["specimen tariffresult resultat tarification cotation"],
    # SpecificSite (ssit.htm)
    "RegisterNonconformity":["registernonconformity creer non-conformite nc enregistrement"],
    "GetNonconformity":     ["getnonconformity verifier non-conformite nc type liste"],
    "GetDepartment":        ["getdepartment departement mnemonic discipline"],
    "GetEncounter":         ["getencounter visite rencontre id"],
    "GetStay":              ["getstay sejour hospitalization id"],
    "GetHLAAntigen":        ["gethlaantigen hla antigene immunologie"],
    "GetProvision":         ["getprovision disposition labo departement"],
    "GetDiagnosisCode":     ["getdiagnosiscode code diagnostic systeme icd"],
    "ExonerationFraction":  ["exemption fraction remboursement france ald cmu assurance"],
    "ExonerationJustification": ["exoneration justification code france assurance"],
    # Fonctions Result (rslt.htm)
    "ResultCancel":             ["result cancel annuler discontinuer repeter diluer raison"],
    "ResultNumericValue":       ["result numericvalue valeur numerique fractional inferieur superieur <  >"],
    "ResultRelatedResult":      ["result relatedresult resultat associe meme objet meme heure prelevement"],
    "ResultGetPriorResult":     ["result getpriorresult antecedent precedent historique valide index"],
    "ResultPriorAttribute":     ["result priorattribute attribut antecedent precedent historique"],
    "ResultAddExternalComment": ["result addexternalcomment ajouter commentaire externe"],
    "ResultAddInternalComment": ["result addinternalcomment ajouter commentaire interne"],
    "ResultSetManualSeverity":  ["result setmanualseverity seuil alerte manuel couleur affichage"],
    "ResultSetAsBaseLine":      ["result setasbaseline valeur initiale baseline delta bornes"],
    "ResultSetAutomaticConfirmation": ["result setautomaticconfirmation confirmation automatique"],
    "ResultSetAutomaticValidation":   ["result setautomaticvalidation validation automatique"],
    "ResultMarkAsSolicited":    ["result markassolicited marquer sollicite non sollicite"],
    "ResultEscalate":           ["result escalate escalade"],
    "ResultGetCode":            ["result getcode code systeme codage loinc"],
    "ResultGetDilutionCode":    ["result getdilutioncode code dilution diluer"],
    "ResultReferenceValue":     ["result referencevalue valeurs reference normes"],
    "ResultReportedNonconformity": ["result reportednonconformity nc non-conformite rapport"],
    "ResultBloodSelectionPromotion":       ["result bloodselectionpromotion promouvoir selection sang compatible"],
    "ResultBloodSelectionDiscontinuation": ["result bloodselectiondiscontinuation discontinuer sang incompatible"],
    "ResultStatisticalWeight":  ["result statisticalweight poids statistique"],
    # Fonctions Action (actn.htm)
    "ActionAttribute":          ["action attribute inputspecimen inputspecimenlist samplingtime position normalposition propertylist objectattributelist issuer agent"],
    "ActionCancel":             ["action cancel annuler resultats sortie action"],
    "ActionInputResult":        ["action inputresult resultat entree analyse"],
    "ActionOutputResult":       ["action outputresult resultat sortie analyse liste travail"],
    "ActionInputByMnemonic":    ["action inputbymnemonic valeur entree analyse mnemonic"],
    "ActionResultOperation":    ["action resultoperation operation comparaison deux resultats"],
    "ActionPropertyList":       ["action propertylist liste analyses action statut"],
    "ActionOrder":              ["action order dossier associe navigation"],
    # ScheduleReports
    "OrderScheduleReports":     ["order schedulereports planifier comptes-rendus automatique apres addrequest cascaderequest"],
    # Correspondent (crsp.htm)
    "CorrespondentAttribute":        ["correspondent attribute attribut TourMnemonicList liste tournees"],
    "CorrespondentIdentification":   ["correspondent identification code ipp numero patient source"],
    "CorrespondentIdentificationList":["correspondent identificationlist liste identifications source date"],
    "CorrespondentHCCode":           ["correspondent hccode code sante riziv inami medecin"],
    "CorrespondentCurrentAgreements":["correspondent currentagreements accords paiement validite"],
    "CorrespondentGroupMembership":  ["correspondent groupmembership groupe appartenance tournee"],
    "CorrespondentCreateIdentification":["correspondent createidentification creer identification code debut fin"],
    # Object (obj.htm) — très utilisé pour âge/attributs patient
    "ObjectAge":              ["object age age patient string format afficher"],
    "ObjectAgeInDays":        ["object ageindays age jours fractional calcul"],
    "ObjectAgeInMonths":      ["object ageinmonths age mois fractional calcul"],
    "ObjectAgeInYears":       ["object ageinyears age annees fractional calcul"],
    "ObjectAttributeList":    ["object attributelist liste attributs objet flags actifs"],
    "ObjectAttributePeriod":  ["object attributeperiod duree attribut jours actif"],
    "ObjectPerson":           ["object person personne patient navigation"],
    "ObjectGetResult":        ["object getresult resultat analyse historique objet"],
    # Person (prsn.htm)
    "PersonGetMedicalRecord": ["person getmedicalrecord dossier medical groupe sanguin rhesus"],
    "PersonSendMail":         ["person sendmail envoyer mail patient email"],
    # Station (stn.htm)
    "StationPrintLabels":     ["station printlabels imprimer etiquettes labels"],
    "StationAttribute":       ["station attribute attribut analyseur station"],
    # Request (rqst.htm)
    "RequestOrder":           ["request order dossier demande navigation"],
    "RequestSpecimen":        ["request specimen echantillon demande navigation"],
    # WorkList (wlt.htm)
    "WorkListAttribute":      ["worklist attribute attribut liste travail label"],
    # User (usr.htm)
    "UserHasPrivilege":       ["user hasprivilege privilege role droits acces"],
    "UserSendMailMethod":     ["user sendmail envoyer mail utilisateur interne"],
    # Encounter (enct.htm)
    "EncounterAttribute":     ["encounter attribute attribut visite hospitalisation"],
    # MicrobiologyAction (mcra.htm)
    "McraAddCarrier":         ["microbiology addcarrier plaque milieu microbiologie"],
    "McraGetIsolation":       ["microbiology getisolation isolement germe bacterie"],
    # Diagnosis (diag.htm)
    "DiagnosisCode":          ["diagnosis code diagnostique icd cim systeme"],
    # BloodBag (bbag.htm)
    "BloodBagCreateOrder":    ["bloodbag createorder dossier transfusion sang poche"],
    # ── Fonctions KB v3 ─────────────────────────────────────────────────────
    "MicrobiologicHistory":   ["objet historique microbiologique bacteries germes antecedents microbiologie"],
    "BuildHistoryGraph":      ["graphique historique xml resultat evolution courbe"],
    "AttributePeriod":        ["duree attribut objet jours actif periode"],
    "PatientData":            ["donnees patient liste attributs format"],
    "PersonData":             ["donnees personne patient attributs"],
    "TariffResultExt":        ["tarification cotation resultat nomenclature NGAP NABM"],
    "BloodSelectionDiscontinuation": ["discontinuation sang poche incompatible annuler selection"],
    "BloodSelectionPromotion":       ["promouvoir selection sang compatible valider poche"],
    "GetDilutionCode":               ["code dilution diluer echantillon"],
    "HLAAntibody":            ["anticorps hla immunologie rejection greffe"],
    "HLAAntigen":             ["antigene hla typage immunologique"],
    "RhesusPhenoType":        ["phenotype rhesus groupe sanguin transfusion"],
    "GetEncountersList":      ["liste hospitalisations visites ouvertes patient"],
    "GetMedicalRecordKB":     ["dossier medical groupe sanguin antecedent"],
    "OtherAntigens":          ["autres antigenes groupe sanguin phenotype"],
    "RelationsOverview":      ["relations patient famille liens parentaux"],
    "PutTag":                 ["inserer tag modifier cle valeur liste taguee"],
    "RangeLabel":             ["tranche intervalle label classe valeur numerique"],
    "RemoveEntry":            ["supprimer element liste position compter"],
    "KnownIdentification":    ["identification connue externe id source date validite"],
    "TourMnemonicList":       ["liste tournees collecte correspondant pattern"],
    "GetDepartment":          ["recuperer departement discipline laboratoire mnemonic"],
    "GetProvision":           ["disposition provision laboratoire departement analyseur"],
    "IsolationTestCount":     ["compter tests isolement microbiologie"],
    "GetSequence":            ["sequence isolement type microbiologie"],
    "VerificationPassed":     ["verification pretransfusionnelle passe effectuee ok"],
    "SetStatusValidated":     ["valider examen pathologie validation finale"],
    "ChangeResponsible":      ["changer responsable pathologiste biologiste"],
    "RegisterNonconformity":  ["enregistrer creer nc non-conformite contexte type"],
    "AskChoice":              ["demander choix dialog boite liste selection obligatoire"],
    "AskString":              ["demander texte saisie utilisateur champ"],
    "AskYesNo":               ["demander oui non confirmation dialog"],
    "GetRole":                ["recuperer role garde biologiste sc_role mnemonic envoyer mail role"],
    "RoleSendMail":           ["envoyer mail role garde biologiste tous utilisateurs GetRole SendMail alerte"],
    # Peek/Poke renforcés
    "PeekCharacter":       ["lire variable partagee chaine shared string peek PeekCharacter peek character variable string partagee biologiste garde"],
    "PokeCharacter":       ["ecrire variable partagee chaine shared string poke PokeCharacter poke character variable string partagee biologiste garde"],
    "PeekDate":            ["lire variable partagee date PeekDate peek date shared"],
    "PeekInteger":         ["lire variable partagee entier PeekInteger peek integer shared"],
    "PokeInteger":         ["ecrire variable partagee entier PokeInteger poke integer shared"],
}


def _enrich_bm25_text(chunk: dict) -> str:
    """
    Construit le texte BM25 enrichi :
    - texte original
    - nom de fonction répété 3x (boost TF)
    - synonymes FR/EN de la fonction (pour matching depuis questions en français)
    - signature
    """
    parts = [chunk["text"]]
    fn = chunk.get("function_name", "")
    if fn:
        # Répéter le nom pour booster son TF dans BM25
        parts.append(f"{fn} {fn} {fn}")
        # Sous-mots PascalCase
        sub = re.findall(r"[A-Z][a-z0-9]+", fn)
        if sub:
            parts.append(" ".join(sub) * 2)
        # Synonymes FR/EN
        syns = _FN_SYNONYMS.get(fn, [])
        for s in syns:
            parts.append(s)
    sig = chunk.get("signature", "")
    if sig:
        parts.append(sig)
    return " ".join(parts)


# ── Chargement singleton ───────────────────────────────────────────────────────

class _RetrieverState:
    """Singleton portant collection ChromaDB + index BM25 chargés une fois."""
    _instance: "_RetrieverState | None" = None

    def __init__(self, use_openai: bool):
        self.use_openai = use_openai
        self._load_chroma(use_openai)
        self._load_bm25()

    def _load_chroma(self, use_openai: bool) -> None:
        if use_openai:
            api_key = os.environ.get("OPENAI_API_KEY", "")
            ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=api_key, model_name="text-embedding-3-small"
            )
        else:
            ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="paraphrase-multilingual-MiniLM-L12-v2"
            )
        client = chromadb.PersistentClient(path=str(VECTORSTORE_PATH))
        self.collection = client.get_collection(name=COLLECTION_NAME, embedding_function=ef)

    def _load_bm25(self) -> None:
        if not BM25_CORPUS_PATH.exists():
            raise FileNotFoundError(
                f"Corpus BM25 absent : {BM25_CORPUS_PATH}\n"
                "Lancer d'abord : python src/rag/build_vectorstore.py"
            )
        with open(BM25_CORPUS_PATH, encoding="utf-8") as f:
            data = json.load(f)

        self.bm25_chunks: list[dict[str, Any]] = data["chunks"]
        self.known_functions: set[str] = set(data.get("known_functions", []))

        # Construire index BM25 avec texte enrichi (function_name boosté x3)
        tokenized_corpus = [_tokenize(_enrich_bm25_text(c)) for c in self.bm25_chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)

    @classmethod
    def get(cls, use_openai: bool = False) -> "_RetrieverState":
        if cls._instance is None or cls._instance.use_openai != use_openai:
            cls._instance = cls(use_openai)
        return cls._instance

    @classmethod
    def invalidate(cls) -> None:
        """Forcer le rechargement au prochain appel (utile après rebuild)."""
        cls._instance = None


# ── RRF ───────────────────────────────────────────────────────────────────────

def _reciprocal_rank_fusion(
    dense_ids: list[str],
    bm25_ids: list[str],
    k: int = RRF_K,
) -> list[tuple[str, float]]:
    """
    Fusionne deux classements par Reciprocal Rank Fusion.
    Retourne liste triée de (id, score_rrf) décroissant.
    """
    scores: dict[str, float] = {}
    for rank, doc_id in enumerate(dense_ids):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    for rank, doc_id in enumerate(bm25_ids):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# ── Reorder anti-Lost-in-the-Middle ──────────────────────────────────────────

def _reorder_for_llm(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Liu et al. 2023 : LLM lit mieux position #1 et #last.
    Meilleur chunk → position 1, second meilleur → position last.
    Reste au milieu (moins important mais nécessaire pour recall).
    """
    if len(docs) <= 2:
        return docs
    sorted_docs = sorted(docs, key=lambda d: d["score"], reverse=True)
    reordered = [sorted_docs[0]]
    reordered.extend(sorted_docs[2:])
    reordered.append(sorted_docs[1])
    return reordered


# ── Query Expansion — intent → mots-clés MISPL ───────────────────────────────

# Table d'expansion : intent FR → tokens MISPL techniques injectés dans la query
_INTENT_EXPANSIONS: list[tuple[list[str], str]] = [
    # Création / ajout demandes — inclut "créer analyse", reflex testing, résultat anormal
    (["creer demande", "ajouter demande", "ajouter analyse", "créer demande", "nouvelle demande",
      "add request", "addrequest", "creer analyse", "créer analyse", "nouvelle analyse",
      "demande glucose", "demande analyse", "prescrire analyse", "commander analyse",
      "automatiquement une analyse", "analyse suite", "analyse complementaire",
      "analyse complementaire", "analyse de confirmation", "reflex", "reflexe",
      "resultat anormal", "valeur anormale", "seuil depasse", "declencher analyse",
      "ajouter automatiquement", "ajout automatique analyse"],
     "Order.AddRequest AddRequest RequestList analyses ajouter dossier Result déclencheur"),
    # Itérer échantillons
    (["parcourir echantillon", "boucle echantillon", "lister echantillon", "iterer specimen",
      "getspecimen", "tous les echantillons"],
     "Order.GetSpecimen GetSpecimen Specimen boucle WHILE iteration"),
    # Valeur résultat numérique + comparaison seuil
    (["valeur numerique", "valeur resultat", "numericvalue", "comparer resultat",
      "< résultat", "> résultat", "resultat anormal", "depasse seuil",
      "seuil anormalite", "valeur anormale", "superieur a", "inferieur a",
      "result value", "attribute value"],
     "Result.NumericValue NumericValue Result.Attribute Value StringToFractional"),
    # Annuler résultat
    (["annuler resultat", "discontinuer", "repeter resultat", "cancel result", "cancelresult"],
     "Result.Cancel Cancel Discontinue Repeat Dilute raison reason"),
    # Non-conformité
    (["non-conformite", "non conformite", "nc ", "enregistrer nc", "créer nc", "nonconformity"],
     "RegisterNonconformity GetNonconformity Nonconformity NCType"),
    # Commentaire résultat
    (["commentaire", "ajouter commentaire", "comment externe", "comment interne"],
     "Result.AddExternalComment AddInternalComment commentaire append text"),
    # Sévérité / alerte
    (["severite", "seuil alerte", "severity", "couleur", "manualseverity"],
     "Result.SetManualSeverity SetManualSeverity alerte severity"),
    # Attributs dossier — toutes valeurs AttributeName fréquentes
    (["liste analyses dossier", "analyses dossier", "propertylist dossier",
      "materiels dossier", "materiallist", "liste materiels",
      "postes de travail", "poste de travail", "workplace", "workplacecode",
      "codes postes", "lieu de travail", "lieux de travail",
      "codes analyseurs", "analyseur dossier", "station dossier", "stationcode",
      "specimens dossier", "liste echantillons", "specimenlist",
      "demandes dossier", "liste demandes", "requestlist", "demandes actives",
      "demandes non discontinuees", "demandes sans discontinuation", "excludediscontinued",
      "demandes en cours", "analyses actives dossier", "codes demande"],
     "Order.Attribute AttributeName PropertyList MaterialList SpecimenList RequestList RequestList:ExcludeDiscontinued StationCodeList WorkPlaceCodeList"),
    # Identifiant / numérotation
    (["id interne", "identifiant", "numerotation", "identifier", "sequence"],
     "Identifier DatedIdentifier NextValue Sequence SpecimenInternalId"),
    # Envoyer email / mail — prescripteur, résultat critique, notification
    (["envoyer email", "envoyer mail", "sendmail", "email mispl",
      "email prescripteur", "mail prescripteur", "notifier prescripteur",
      "notification prescripteur", "alerter prescripteur", "alerte critique",
      "resultat critique", "email medecin", "mail medecin", "envoyer notification",
      "envoyer alerte", "prevenir prescripteur", "informer prescripteur",
      "issuer email", "issuer mail", "issuer sendmail"],
     "SendMail Correspondent.SendMail sc_User.SendMail MailPriority From To Subject Issuer GetCorrespondent"),
    # Formatter date
    (["formater date", "format date", "afficher date", "datetostring", "strftime"],
     "DateToString DateTimeToString format %d %m %Y Today Now"),
    # Sous-chaîne / extraction chaîne — Substr en premier pour l'exact-match prioritaire
    (["sous-chaine", "extraire chaine", "substring", "substr", "partie chaine",
      "extraire caractere", "premiers caracteres", "derniers caracteres",
      "caracteres chaine", "tronquer chaine", "couper chaine",
      "longueur chaine", "taille chaine", "len chaine", "length string",
      "remplacer chaine", "chercher chaine", "position chaine",
      "manipulation chaine", "manipulation string", "traitement chaine"],
     "Substr Substr Substr Len Index Replace NumEntries function_string"),
    # Planifier CR
    (["planifier compte-rendu", "créer cr", "report", "schedulereports"],
     "Order.ScheduleReports ScheduleReports CreateReport CreateMediumReport"),
    # Stockage sérothèque
    (["serotheque", "stockage", "stocker echantillon", "setstorage", "getstorage"],
     "Specimen.SetStorage SetStorage GetStorage ArchiveMnemonic portoir"),
    # Microbiologie
    (["plaque", "microbiologie", "carrier", "milieu", "addcarriers"],
     "Specimen.AddCarriers AddCarriers MediumMnemonicList microbiologie"),
    # Âge patient
    (["age patient", "age objet", "calculer age", "age en ans", "age en mois",
      "age en jours", "ageinyears", "ageindays", "ageinmonths"],
     "Object.Age Object.AgeInYears Object.AgeInDays Object.AgeInMonths ReferenceDate"),
    # Attributs objet patient
    (["attribut objet", "attribut patient", "attributelist", "flags attribut",
      "attribut actif", "periode attribut", "attributeperiod"],
     "Object.AttributeList AttributeList AttributePeriod FlagList MinimalSeverity"),
    # Identification patient / IPP
    (["identification patient", "ipp", "numero patient", "id patient",
      "identification correspondant", "createidentification", "identificationlist",
      "numero ipp", "identifiant patient", "nip ", "nimm",
      "numéro national", "numero national", "pin patient",
      "recuperer ipp", "lire ipp", "obtenir ipp", "extraire ipp"],
     "Correspondent.Identification Identification IdentificationList CreateNationalNumber SourceInternalId crsp"),
    # Résultat antérieur / historique
    (["resultat anterieur", "precedent resultat", "historique resultat",
      "comparer avec avant", "getpriorresult", "priorattribute", "delta"],
     "Result.GetPriorResult GetPriorResult PriorAttribute Index historique"),
    # Reflex testing — ajouter analyse si autre analyse anormale (pattern très fréquent en labo)
    (["si hemoglobine", "si hb ", "hemoglobine < ", "hb <", "hemoglobine inferieure",
      "ajouter reticulocytes", "reticulocytes si", "reflexe reticulocyte",
      "analyse conditionnelle", "si resultat inferieur", "si valeur inferieure",
      "si analyse anormale", "ajouter si", "declencher si resultat",
      "analyse complementaire si", "reflex test", "bilan complementaire si"],
     "Result.NumericValue NumericValue Result.RelatedResult RelatedResult Order.AddRequest AddRequest ScheduleReports"),
    # Groupe sanguin / dossier médical
    (["groupe sanguin", "rhesus", "dossier medical", "getmedicalrecord",
      "bloodgroup", "transfusion conseil"],
     "Person.GetMedicalRecord GetMedicalRecord BloodGroup Rhesus TransfusionAdvice"),
    # Imprimer étiquettes
    (["imprimer etiquette", "etiquette", "label", "printlabels", "imprimante"],
     "PrintLabels GetPrinterId rp_Printer LabelPrinterId Station"),
    # Navigation Object.Person / Person.Object
    (["naviguer personne", "person navigation", "objet patient", "object person",
      "patient objet", "personne objet"],
     "Object.Person Person() navigation correspondent"),
    # Résultat pour analyse via objet
    (["dernier resultat", "resultat objet", "getresult objet", "result for object"],
     "Object.GetResult GetResult PropertyMnemonic historique"),
    # Droits/privilèges utilisateur
    (["privilege", "droit", "hasprivilege", "role utilisateur", "acces fonction"],
     "HasPrivilege sc_User privilege role CurrentUser CurrentRole"),
    # Action.PropertyList — analyses en sortie d'une action
    (["analyses sortie action", "analyses en sortie", "liste analyses action",
      "propertylist action", "resultats action", "analyses planifiees action",
      "analyses produites action", "outputs action", "sorties action"],
     "Action.PropertyList PropertyList MinimalStatus MaximalStatus AllowUnsolicitedResults actn"),
    # Action.OutputResult — résultat spécifique en sortie
    (["outputresult", "resultat sortie action", "output result action",
      "resultat produit action", "resultat action mnemonic"],
     "Action.OutputResult OutputResult PropertyMnemonic actn"),
    # Action.Attribute — attributs de l'action
    (["attribut action", "position action", "samplingtime action",
      "heure prelevement action", "inputspecimen action", "propertylist action"],
     "Action.Attribute Attribute InputSpecimen SamplingTime Position PropertyList actn"),
    # Contexte Result → script déjà sur le résultat courant
    (["si hemoglobine", "si hb ", "hemoglobine < ", "hb <", "resultat courant",
      "script sur resultat", "result context", "contexte result", "depuis le resultat"],
     "Result.NumericValue NumericValue Action Order AddRequest résultat courant context"),

    # ── Nouveaux patterns ─────────────────────────────────────────────────────

    # Calcul delta / baseline / variation résultat
    (["delta", "variation resultat", "change depuis", "difference valeur",
      "comparaison baseline", "valeur baseline", "evol resultat", "baseline"],
     "Result.SetAsBaseLine SetAsBaseLine Result.GetPriorResult GetPriorResult baseline delta variation"),

    # Bornes de référence / valeurs normales
    (["bornes reference", "valeurs reference", "normes", "seuil normal",
      "valeur seuil", "reference patient", "intervalle normal", "normes labo",
      "limites normalite", "referencevalue", "valeur normale"],
     "Result.ReferenceValue ReferenceValue seuil normal intervalle"),

    # Textes dynamiques / modules texte
    (["texte dynamique", "interpoler", "module texte", "generer texte",
      "texte avec variable", "texte template", "dynamic text",
      "texte compte rendu", "module mnemonic", "substitution variable"],
     "Expand texte dynamique {= expression {: programme {< Module interpolation"),

    # Validation / confirmation automatique résultat
    (["validation automatique", "confirmation automatique", "auto validate",
      "auto confirm", "valider automatiquement", "confirmer automatiquement"],
     "Result.SetAutomaticValidation SetAutomaticValidation Result.SetAutomaticConfirmation SetAutomaticConfirmation"),

    # Dilution / répétition résultat
    (["dilution", "diluer resultat", "repeter analyse", "code dilution",
      "getdilutioncode", "dilution code", "diluer echantillon"],
     "Result.GetDilutionCode GetDilutionCode Result.Cancel Cancel Dilute Repeat dilution"),

    # Transfusion / compatibilité sang
    (["sang incompatible", "incompatibilite sang", "compatibilite sang",
      "selection sang", "epreuve compatibilite", "transfusion compatible",
      "bloodselection", "poche sang", "transfusion"],
     "Result.BloodSelectionPromotion BloodSelectionPromotion Result.BloodSelectionDiscontinuation BloodSelectionDiscontinuation BloodSelection"),

    # Escalade résultat critique
    (["escalade resultat", "escalader", "result escalate", "escalade critique"],
     "Result.Escalate Escalate escalade critique"),

    # Jours fériés / urgence
    (["jour ferie", "jour ferié", "holiday", "urgence", "isholiday",
      "specimen urgency", "urgency specimen"],
     "IsHoliday holiday Specimen.Attribute Urgency urgence"),

    # Microbiologie — comptage plaques / isolements
    (["compter plaques", "carrier count", "isolation count", "compter isolements",
      "germe organisme", "antibiogramme", "aerobie", "isolement micro"],
     "Specimen.CarrierCount CarrierCount Specimen.IsolationCount IsolationCount MicrobiologyAction antibiogramme"),

    # Pathologie / histologie
    (["pathologie", "histologie", "bloc pathologie", "addblocks",
      "pathology exam", "examen pathologie"],
     "Specimen.AddBlocks AddBlocks PathologyExam pathologie histologie"),

    # Première / dernière demande specimen
    (["premiere demande specimen", "derniere demande specimen",
      "first request specimen", "last request specimen"],
     "Specimen.FirstRequest FirstRequest Specimen.LastRequest LastRequest"),

    # Listes délimitées — Entry, NumEntries, Sort
    (["element liste", "extraire element liste", "compter elements liste",
      "trier liste", "sort list", "numentries", "separator delimiter",
      "entree liste", "entry index"],
     "NumEntries Entry Sort liste delimiter separator Lookup"),

    # Codes diagnostiques ICD/CIM
    (["code diagnostic", "icd cim", "diagnostic ordre", "getdiagnosis",
      "diagnostic iterer", "cim10", "icd10"],
     "Order.GetDiagnosis GetDiagnosis GetDiagnosisCode DiagnosisCode ICD CIM diagnostic"),

    # Tâches todo ordre
    (["tache todo", "creer tache", "liste taches ordre", "addordertodoitem",
      "todo item", "due date tache"],
     "Order.AddOrderTodoItem AddOrderTodoItem OrderTodoItem tache todo"),

    # Tarification / facturation / nomenclature
    (["facture", "tarification", "budget invoice", "elements facture",
      "nomenclature codes", "tariff result", "billing", "cotation"],
     "Order.BudgetInvoice BudgetInvoice Order.InvoiceItemsData InvoiceItemsData Specimen.TariffResult nomenclature"),

    # FSE — Feuille Soins Électronique (France)
    (["fse", "feuille soins electronique", "check fse", "erreur fse",
      "checkfse", "secu france"],
     "Order.CheckFSE CheckFSE FSE France feuille soins electronique"),

    # Format valeur résultat (Browse/Report/Work/Online)
    (["format affichage resultat", "format rapport resultat", "browseformat",
      "reportformat", "workformat", "onlineformat", "rawformat"],
     "Result.Attribute Value:BrowseFormat Value:ReportFormat Value:WorkFormat Value:OnlineFormat Value:RawFormat"),

    # HLA / immunologie
    (["hla", "antigene hla", "typage hla", "immunologie hla",
      "gethlaantigen", "hla typing"],
     "GetHLAAntigen HLAAntigen HLA typage immunologie"),

    # Exemptions / remboursement France (ALD, CMU, FSV)
    (["exemption", "remboursement ald", "cmu fsv", "fraction remboursement",
      "exoneration", "code situation assurance", "code regime"],
     "ExonerationFraction ExonerationJustification ExonerationNature ALD CMU FSV remboursement"),

    # Résultat non-sollicité / sollicité
    (["non sollicite", "unsolicited", "marquer sollicite", "sollicite",
      "markassolicited"],
     "Result.MarkAsSolicited MarkAsSolicited unsolicited sollicited"),

    # Poids statistique
    (["poids statistique", "statistical weight", "ponderation analyse"],
     "Result.StatisticalWeight StatisticalWeight poids statistique"),

    # Journal audit / log
    (["ajouter journal", "journal log", "trace audit", "audit trail",
      "historique action", "enregistrer log", "log entry", "addlogentry"],
     "AddLogEntry GetLogEntry journal audit trace log entry historique"),

    # Journal téléphonique / appels
    (["telephone resultat", "appel prescripteur", "phonelog",
      "marquer telephoner", "to be phoned", "journal telephone"],
     "Order.GetPhoneLog GetPhoneLog Order.ToBePhoned ToBePhoned phoned telephone"),

    # Successeur / prédécesseur résultat
    (["resultat suivant", "successeur resultat", "successor",
      "chaine resultats", "resultat apres"],
     "Result.Successor Successor predecessor chaine resultats"),

    # Navigation ERD multi-tables
    (["naviguer entre tables", "naviguer erd", "traverser relation",
      "acceder depuis", "navigation glims", "lien entre tables"],
     "Order() Action() Result() Specimen() Object() Person() navigation ERD relation"),

    # StatisticalWeight / poids analyse
    (["opération deux resultats", "comparer deux analyses",
      "resultatoperation", "rapport mesures"],
     "Action.ResultOperation ResultOperation comparaison deux analyses"),
]

_INTENT_EXPANSIONS_NORM = [
    ([_normalize(t.lower().replace("-", " ")) for t in triggers], expansion)
    for triggers, expansion in _INTENT_EXPANSIONS
]


def _fuzzy_trigger_match(trigger: str, query_norm: str, min_len: int = 6) -> bool:
    """Matching flou : substring exact + préfixe 80% (absorbe troncatures/fautes finales)."""
    if trigger in query_norm:
        return True
    if len(trigger) >= min_len:
        prefix_len = max(min_len, int(len(trigger) * 0.8))
        if trigger[:prefix_len] in query_norm:
            return True
    return False


def _expand_query(query: str) -> str:
    """
    Enrichit la requête avec des tokens MISPL techniques inférés de l'intent utilisateur.
    Substring exact + fuzzy prefix (80%). Pas d'appel LLM : latence nulle, déterministe.
    Ex: "créer une demande d'analyse" → ajoute "Order.AddRequest AddRequest RequestList..."
    """
    q_norm = _normalize(query.lower().replace("-", " "))
    additions: list[str] = []
    for triggers, expansion in _INTENT_EXPANSIONS_NORM:
        if any(_fuzzy_trigger_match(t, q_norm) for t in triggers):
            additions.append(expansion)
    if additions:
        return query + " " + " ".join(additions)
    return query


# ── Interface publique ─────────────────────────────────────────────────────────

class MISPLRetriever:
    """
    Retriever hybride BM25 + dense avec exact-match boost et reorder anti-LiM.
    Usage :
        r = MISPLRetriever()
        docs = r.query("comment extraire une sous-chaîne ?")
        context = r.format_context(docs)
    """

    def __init__(self, use_openai: bool = False, top_k: int = 6):
        self.top_k = top_k
        self._state = _RetrieverState.get(use_openai)

    # ── Détection exact-match ──────────────────────────────────────────────────

    def _detect_function_name(self, query: str) -> str | None:
        """Retourne le nom de fonction MISPL si trouvé verbatim dans la query."""
        tokens = set(re.findall(r"[A-Za-z][A-Za-z0-9]+", query))
        match = tokens & self._state.known_functions
        if match:
            # Préférer le token le plus long (évite 'Log' vs 'Log10')
            return max(match, key=len)
        return None

    # ── Recherche dense ────────────────────────────────────────────────────────

    def _dense_search(self, query: str, n: int) -> list[dict[str, Any]]:
        results = self._state.collection.query(
            query_texts=[query],
            n_results=min(n, self._state.collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        docs = []
        for i in range(len(results["ids"][0])):
            docs.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "score": float(1.0 - results["distances"][0][i]),
                **{k: results["metadatas"][0][i].get(k, "") for k in [
                    "source", "section", "doc_title", "function_name",
                    "return_type", "signature", "category", "priority",
                    "has_examples", "is_table_independent",
                ]},
            })
        return docs

    # ── Recherche BM25 ─────────────────────────────────────────────────────────

    def _bm25_search(self, query: str, n: int) -> list[dict[str, Any]]:
        tokens = _tokenize(query)
        scores = self._state.bm25.get_scores(tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n]
        docs = []
        for idx in top_indices:
            if scores[idx] <= 0:
                break
            c = self._state.bm25_chunks[idx]
            docs.append({
                "id": c["id"],
                "text": c["text"],
                "score": float(scores[idx]),
                "source": c.get("source", ""),
                "section": c.get("section", ""),
                "doc_title": c.get("source", ""),
                "function_name": c.get("function_name", ""),
                "return_type": c.get("return_type", ""),
                "signature": c.get("signature", ""),
                "category": c.get("category", ""),
                "priority": c.get("priority", False),
                "has_examples": c.get("has_examples", False),
                "is_table_independent": False,
            })
        return docs

    # ── Exact-match override ───────────────────────────────────────────────────

    def _exact_match_search(self, function_name: str) -> list[dict[str, Any]]:
        """
        Recherche directe par nom de fonction dans ChromaDB.
        Score = 1.0 garantit la position #1 dans le résultat final.
        """
        try:
            results = self._state.collection.query(
                query_texts=[function_name],
                n_results=3,
                where={"function_name": function_name},
                include=["documents", "metadatas", "distances"],
            )
            docs = []
            for i in range(len(results["ids"][0])):
                docs.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "score": 1.0,  # exact match → certitude maximale
                    "exact_match": True,
                    **{k: results["metadatas"][0][i].get(k, "") for k in [
                        "source", "section", "doc_title", "function_name",
                        "return_type", "signature", "category", "priority",
                        "has_examples", "is_table_independent",
                    ]},
                })
            return docs
        except Exception:
            return []

    # ── Query principal ────────────────────────────────────────────────────────

    def query(
        self,
        question: str,
        top_k: int | None = None,
        category_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Recherche hybride BM25 + dense + exact-match avec reorder anti-LiM.

        Args:
            question: Question en langage naturel ou nom de fonction MISPL
            top_k: Nombre de résultats finaux (défaut: self.top_k)
            category_filter: Filtrer par catégorie ('string', 'datetime', 'math'...)

        Returns:
            Liste de chunks triés, reordonnés pour minimiser lost-in-middle
        """
        k = top_k or self.top_k
        fetch_n = k * 6  # fetch large : couvre les cas où le bon doc est rang 20+ en dense

        # Health-check collection : après un rebuild, l'UUID en mémoire est mort
        # (Streamlit @cache_resource). On teste et recharge le _state si nécessaire.
        try:
            self._state.collection.count()
        except Exception:
            _RetrieverState.invalidate()
            self._state = _RetrieverState.get(self._state.use_openai)

        # Niveau 1 : exact-match si nom de fonction détecté dans la question
        exact_docs: list[dict[str, Any]] = []
        detected_fn = self._detect_function_name(question)
        if detected_fn:
            exact_docs = self._exact_match_search(detected_fn)

        # Query expansion : enrichit la requête avec mots-clés MISPL inférés de l'intent
        expanded_question = _expand_query(question)

        # Exact-match ciblé sur les tokens de l'expansion
        # Stratégie : prendre seulement les 2 fonctions les plus longues de l'expansion
        # (les plus longues = les plus spécifiques, évite de diluer avec 11 fonctions string)
        if expanded_question != question:
            seen_exact = {d["id"] for d in exact_docs}
            expansion_part = expanded_question[len(question):]
            expansion_tokens = set(re.findall(r"[A-Za-z][A-Za-z0-9]+", expansion_part))
            # Priorité : fonctions aussi présentes dans la query originale (plus pertinentes)
            orig_tokens = set(re.findall(r"[A-Za-z][A-Za-z0-9]+", question.lower()))
            fn_hits = expansion_tokens & self._state.known_functions
            # Scorer : +2 si token présent dans query originale, sinon longueur
            def _fn_priority(fn: str) -> int:
                return len(fn) + (20 if fn.lower() in orig_tokens else 0)
            for fn in sorted(fn_hits, key=_fn_priority, reverse=True)[:2]:  # max 2
                if fn == detected_fn:
                    continue
                for d in self._exact_match_search(fn):
                    if d["id"] not in seen_exact:
                        exact_docs.append(d)
                        seen_exact.add(d["id"])

        # Niveau 2 : dense + BM25 (sur requête expandée)
        dense_docs = self._dense_search(expanded_question, fetch_n)
        bm25_docs = self._bm25_search(expanded_question, fetch_n)

        # RRF
        dense_ids = [d["id"] for d in dense_docs]
        bm25_ids = [d["id"] for d in bm25_docs]
        rrf_ranked = _reciprocal_rank_fusion(dense_ids, bm25_ids)

        # Construire dict id → doc pour lookup rapide
        all_docs_map: dict[str, dict[str, Any]] = {}
        for d in dense_docs + bm25_docs:
            if d["id"] not in all_docs_map:
                all_docs_map[d["id"]] = d

        # Assembler résultats RRF
        rrf_docs: list[dict[str, Any]] = []
        seen_ids: set[str] = set(d["id"] for d in exact_docs)
        for doc_id, rrf_score in rrf_ranked:
            if doc_id in seen_ids:
                continue
            if doc_id in all_docs_map:
                doc = all_docs_map[doc_id].copy()
                doc["score"] = rrf_score
                doc["exact_match"] = False
                if category_filter and doc.get("category") != category_filter:
                    continue
                rrf_docs.append(doc)
                seen_ids.add(doc_id)
            if len(rrf_docs) >= k * 2:  # récupérer plus pour le tri suivant
                break

        # Boost multiplicatif post-RRF (préserve la distribution ordinale RRF) :
        #   ×1.12 function_name · ×1.08 catégorie MISPL pure · ×1.04 exemples de code
        for doc in rrf_docs:
            multiplier = 1.0
            if doc.get("function_name"):
                multiplier *= 1.12
            if doc.get("category") in _MISPL_PURE_CATEGORIES:
                multiplier *= 1.08
            if doc.get("has_examples"):
                multiplier *= 1.04
            doc["score"] = doc["score"] * multiplier
        rrf_docs.sort(key=lambda d: d["score"], reverse=True)

        # Fusionner : exact_docs en tête, puis RRF
        combined = exact_docs + rrf_docs
        combined = combined[:k]

        # Reorder anti-Lost-in-the-Middle
        return _reorder_for_llm(combined)

    # ── Formatage contexte pour LLM ────────────────────────────────────────────

    def format_context(self, docs: list[dict[str, Any]]) -> str:
        """
        Formate les chunks pour injection dans le prompt.
        Structure explicite : nom de fonction, signature, source.
        """
        parts = []
        for i, doc in enumerate(docs, 1):
            header_parts = [f"[Doc {i}]"]
            if doc.get("exact_match"):
                header_parts.append("⭐ CORRESPONDANCE EXACTE")
            if doc.get("function_name"):
                header_parts.append(f"Fonction : {doc['function_name']}")
            if doc.get("return_type"):
                header_parts.append(f"Type : {doc['return_type']}")
            header_parts.append(f"Source : {doc.get('source', '?')} — {doc.get('section', '?')}")
            header_parts.append(f"Score : {doc.get('score', 0):.3f}")

            if doc.get("signature"):
                sig_line = f"SIGNATURE CONFIRMÉE : {doc['signature']}"
            else:
                sig_line = ""

            block = "\n".join(header_parts)
            if sig_line:
                block += f"\n{sig_line}"
            block += f"\n\n{doc['text']}"
            parts.append(block)

        return "\n\n" + ("─" * 60) + "\n\n".join(parts)

    @property
    def known_functions(self) -> set[str]:
        return self._state.known_functions


def get_retriever(use_openai: bool = False, top_k: int = 6) -> MISPLRetriever:
    return MISPLRetriever(use_openai=use_openai, top_k=top_k)
