"""
Pipeline d'ingestion GLIMS/MISPL — v2.
Failles corrigées vs v1 :
  - Parser function-aware : un chunk = une fonction MISPL atomique
  - Extraction de signature depuis tableaux HTML (pas get_text() naïf)
  - Métadonnées enrichies : function_name, return_type, category, is_table_independent
  - Encodage : détection automatique (chardet) + fallback latin-1
  - Fichiers à structure plate (sans h3) : parser alternatif par <p><b> ou <font>
  - Overlap augmenté à 400 chars (couvre une signature complète)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import chardet
import chromadb
from bs4 import BeautifulSoup, Tag
from chromadb.utils import embedding_functions
from tqdm import tqdm


# ── Config ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent.parent
DOCS_ROOT = ROOT / "french" / "Content"
VECTORSTORE_PATH = ROOT / "docs" / "chunks" / "vectorstore"
BM25_CORPUS_PATH = ROOT / "docs" / "chunks" / "bm25_corpus.json"
COLLECTION_NAME = "glims_mispl_docs"

CHUNK_MAX_CHARS = 1400
CHUNK_OVERLAP_CHARS = 400  # couvre une signature complète

# Catégories MISPL déduites du chemin de fichier
CATEGORY_MAP = {
    "function_string": "string",
    "function_datetime": "datetime",
    "function_mathematical": "math",
    "function_datatypeconversion": "conversion",
    "function_miscellaneous": "misc",
    "function_interactive": "interactive",
    "function_errormessages": "error",
    "function_billing": "billing",
    "function_readingvariables": "variables",
    "function_writingvariables": "variables",
    "mispl_syntax_grammar": "syntax",
    "mispl_erd": "erd",
    "mispl_table_specific": "table_specific",
    "mispl_performance_tips": "performance",
    "mispl_regular_expressions": "regex",
    "mispl_send_mail": "mail",
    "mispl_introduction": "introduction",
    "mispl_expression_builder": "expression_builder",
    "mispl_testing": "testing",
    "texts_syntax_grammar": "texts",
    "texts_nested": "texts",
    # Fonctions table-spécifiques Order/Specimen/Result
    "orders_m_attribute": "order_table",
    "orders_m_get_identifier": "order_table",
    "orders_m_recalculate_specimen": "order_table",
    "results_m_attribute": "result_table",
    "results_m_workspecimen": "result_table",
    "specimens_m_attribute": "specimen_table",
    "specimens_m_add_request": "specimen_table",
    "specimens_m_collection_info": "specimen_table",
    "specimens_m_directparent": "specimen_table",
    "specimens_m_result": "specimen_table",
    "specimens_m_set_measured_size": "specimen_table",
    "specimens_m_variables": "specimen_table",
    # Reference guide — tables GLIMS clés avec sections MISPL functions
    "ssit": "specificsite_table",   # SpecificSite : RegisterNonconformity, GetNonconformity, GetPrinterId...
    "ord": "order_table",           # Order : AddRequest, GetSpecimen, Result, PropertyList, Summary...
    "spmn": "specimen_table",       # Specimen : AddCarriers, AddBlocks, SetStorage, GetStorage...
    "rslt": "result_table",         # Result : Cancel, NumericValue, RelatedResult, GetPriorResult...
    "actn": "action_table",         # Action : Attribute, Cancel, InputResult, OutputResult...
    # Tables fréquemment utilisées en MISPL quotidien
    "crsp": "correspondent_table",  # Correspondent : Attribute, SendMail, Identification, HCCode, GetPaymentAgreement...
    "obj": "object_table",          # Object : Age, AgeInDays, AgeInYears, AttributeList, Person, GetResult...
    "prsn": "person_table",         # Person : GetMedicalRecord, BloodGroup, SendMail...
    "stn": "station_table",         # Station : PrintLabels, GetPrinterId...
    "prop": "property_table",       # Property : GetResult, ResultFor...
    "mat": "material_table",        # Material : fonctions de matériel
    "mcra": "microbiology_table",   # MicrobiologyAction : AddCarrier, Carrier, Isolation...
    "isol": "isolation_table",      # Isolation : Antibiogram, Organism...
    "bbag": "bloodbag_table",       # BloodBag : fonctions sang/transfusion
    "wlt": "worklist_table",        # WorkList : fonctions listes de travail
    "rqst": "request_table",        # Request : AddRequest, CancelRequest...
    "rprt": "report_table",         # Report : fonctions comptes-rendus
    "usr": "user_table",            # sc_User : SendMail, HasPrivilege...
    "enct": "encounter_table",      # Encounter : fonctions visites
    "dept": "department_table",     # Department : fonctions disciplines
    "nc": "nc_table",               # Nonconformity : Type, Description...
    "stay": "stay_table",           # Stay : fonctions séjours
    "diag": "diagnosis_table",      # Diagnosis : Code, System...
    # Tables supplémentaires avec fonctions MISPL réelles vérifiées
    "gsit": "site_table",           # gp_Site : CurrentSessionHasPrivilege, AddLogEntry, Expand, GetAttachments...
    "ptex": "pathology_table",      # PathologyExam : 10 fonctions pathologie (AddBlock, AddSlide, Conclusion...)
    "os":   "objectstatus_table",   # ObjectStatus : 10 fonctions statuts objet
    "bsel": "bloodselection_table", # BloodSelection : 7 fonctions transfusion
    "carr": "carrier_table",        # Carrier : 5 fonctions microbiologie plaques
    # Contexte et non-conformités
    "nc_mispl": "nonconformity_table",
    "reports_print_responsibles": "order_table",
    "specimens_ids": "specimen_table",
    "order_entry_options_tab_main": "context",
}

PRIORITY_STEMS = set(CATEGORY_MAP.keys())

# Types de retour MISPL connus — pour extraction metadata
MISPL_RETURN_TYPES = {"String", "Integer", "Fractional", "Logical", "Date", "Datetime", "Time", "Void"}

# Noms de fonctions extraits à l'indexation — sérialisés pour BM25 exact-match
KNOWN_FUNCTION_NAMES: set[str] = set()


# ── Détection encodage ─────────────────────────────────────────────────────────

def _read_html(filepath: Path) -> str:
    raw = filepath.read_bytes()
    detected = chardet.detect(raw)
    enc = detected.get("encoding") or "latin-1"
    # Priorité : utf-8 déclaré dans le HTML
    if b"charset=utf-8" in raw[:500].lower() or b'charset="utf-8"' in raw[:500].lower():
        enc = "utf-8"
    try:
        return raw.decode(enc, errors="replace")
    except Exception:
        return raw.decode("latin-1", errors="replace")


# ── Nettoyage texte ────────────────────────────────────────────────────────────

_ENCODING_FIXES = [
    # Artefacts double-encodage UTF-8 interpretes en latin-1
    ("\xe2\x80\xa6",    "..."),   # â€¦ → ...
    ("\xe2\x80\x99",    "'"),     # â€™ → '
    ("\xe2\x80\x9c",    '"'),     # â€œ → "
    ("\xe2\x80\x9d",    '"'),     # â€  → "
    ("\xe2\x80\x94",    "-"),     # â€" → em dash
    ("\xc3\xa9",        "\xe9"),  # Ã© → é
    ("\xc3\xa8",        "\xe8"),  # Ã¨ → è
    ("\xc3\xaa",        "\xea"),  # Ãª → ê
    ("\xc3\xa0",        "\xe0"),  # Ã  → à
    ("\xc3\xae",        "\xee"),  # Ã® → î
    ("\xc3\xb4",        "\xf4"),  # Ã´ → ô
    ("\xc3\xbb",        "\xfb"),  # Ã» → û
    ("\xc3\xa7",        "\xe7"),  # Ã§ → ç
    ("\xc5\x93",        "œ"),# Å" → œ
    ("\xc2\xa0",        " "),     # Â  → espace insecable
    ("\xc2\xab",        "\xab"),  # Â« → «
    ("\xc2\xbb",        "\xbb"),  # Â» → »
    ("\xc2\xb0",        "\xb0"),  # Â° → °
    # Entites HTML
    ("\xa0",  " "), ("&nbsp;", " "), ("&lt;", "<"), ("&gt;", ">"),
    ("&amp;", "&"), ("&quot;", '"'), ("&#160;", " "),
    # Caractere de remplacement Unicode
    ("�", ""),
]

def _clean_text(text: str) -> str:
    for bad, good in _ENCODING_FIXES:
        text = text.replace(bad, good)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" \n", "\n", text)
    return text.strip()


# ── Extraction signature depuis tableau HTML ───────────────────────────────────

def _extract_signature_from_table(table: Tag) -> tuple[str, str, str]:
    """
    Reconstruit 'ReturnType FunctionName(Type Param, ...)' depuis un tableau GLIMS.
    Retourne (signature_str, return_type, function_name).
    Le tableau GLIMS typique a la forme :
      <tr><td>ReturnType</td><td>FunctionName</td><td>(Type1 Param1, ...)</td></tr>
    """
    rows = table.find_all("tr")
    if not rows:
        return "", "", ""

    # Utiliser UNIQUEMENT la première ligne — les lignes suivantes sont des exemples
    # ou des tableaux de paramètres qui parasitent la détection du nom de fonction
    first_row_cells = [td.get_text(separator=" ", strip=True) for td in rows[0].find_all(["td", "th"])]
    cells = first_row_cells
    if not cells:
        return "", "", ""

    # Reconstituer le texte de la première ligne pour signatures mono-cellule
    full_sig_text = " ".join(cells)

    # Garde : si la première ligne ressemble à un tableau d'exemples (contient
    # des guillemets, des chiffres, "rend", "returns") → pas une signature
    _EXAMPLE_MARKERS = ('"', "rend", "returns", "renvoie", "exemple", "example")
    if any(m in full_sig_text.lower() for m in _EXAMPLE_MARKERS):
        return "", "", ""

    return_type = ""
    func_name = ""
    params = ""

    # Détecter le type de retour (peut être en tête de cellule unique ou cellule dédiée)
    for cell in cells:
        for rt in MISPL_RETURN_TYPES:
            if cell.strip().startswith(rt):
                return_type = rt
                break
        if return_type:
            break

    # Chercher le nom de fonction
    # Cas 1 : cellule dédiée contenant uniquement le nom PascalCase
    for cell in cells:
        stripped = cell.strip()
        if re.match(r"^[A-Z][a-zA-Z0-9]+$", stripped) and stripped not in MISPL_RETURN_TYPES:
            func_name = stripped
            break

    # Cas 2 (signatures mono-cellule GLIMS) : "ReturnType FuncName(params...)"
    # ex : "String Substr (String Source, Integer Position, Integer Length)"
    # Mots à exclure : termes de documentation qui ne sont pas des noms de fonctions
    _NOT_FUNC_NAMES = {"Directive", "Description", "Example", "Exemple", "Note",
                       "Parameter", "Param", "Return", "Type", "Format", "Value",
                       "Result", "Output", "Input"}
    if not func_name and return_type:
        m = re.search(
            r"\b" + re.escape(return_type) + r"\b\s+([A-Z][a-zA-Z0-9]+)\s*[\(\s]",
            full_sig_text,
        )
        if m:
            candidate = m.group(1)
            if candidate not in MISPL_RETURN_TYPES and candidate not in _NOT_FUNC_NAMES:
                func_name = candidate

    # Paramètres : cellule avec parenthèses ou reconstitution depuis texte complet
    for cell in cells:
        if "(" in cell:
            params = cell.strip()
            break
    if not params and "(" in full_sig_text:
        params = full_sig_text

    # Construire lignes supplémentaires (surcharges)
    extra_sigs = []
    for row in rows[1:]:
        row_cells = [td.get_text(separator=" ", strip=True) for td in row.find_all(["td", "th"])]
        if row_cells and any(rt in row_cells[0] for rt in MISPL_RETURN_TYPES):
            extra_sigs.append("  " + " ".join(row_cells))

    sig = f"{return_type} {func_name}({params})"
    if extra_sigs:
        sig += "\n" + "\n".join(extra_sigs)

    return sig.strip(), return_type, func_name


# ── Parser function-aware (fichiers MISPL avec h3 par fonction) ────────────────

def _get_category(stem: str) -> str:
    for key, cat in CATEGORY_MAP.items():
        if key in stem:
            return cat
    return "general"


def _is_priority(rel_path: str) -> bool:
    stem = Path(rel_path).stem
    return any(p in stem for p in PRIORITY_STEMS)


def _make_chunk(
    text: str,
    doc_title: str,
    source_path: str,
    idx: int,
    section: str | None,
    function_name: str = "",
    return_type: str = "",
    signature: str = "",
    examples: str = "",
) -> dict[str, Any]:
    uid = hashlib.md5(f"{source_path}_{idx}_{text[:60]}".encode()).hexdigest()
    stem = Path(source_path).stem
    category = _get_category(stem)
    is_table_ind = "mispl_table_independent" in source_path

    if function_name:
        KNOWN_FUNCTION_NAMES.add(function_name)

    return {
        "id": uid,
        "text": text,
        "metadata": {
            "source": source_path,
            "doc_title": doc_title,
            "section": section or doc_title,
            "function_name": function_name,
            "return_type": return_type,
            "signature": signature[:300] if signature else "",
            "has_examples": bool(examples),
            "category": category,
            "is_table_independent": is_table_ind,
            "priority": _is_priority(source_path),
            "char_count": len(text),
        },
    }


def _parse_function_file(filepath: Path, rel_path: str) -> list[dict[str, Any]]:
    """
    Parser spécialisé pour fichiers de référence de fonctions MISPL.
    Chaque h3 = une fonction. Extrait signature depuis tableau.
    """
    html = _read_html(filepath)
    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.find("title") or soup.find("h1")
    doc_title = _clean_text(title_tag.get_text()) if title_tag else filepath.stem

    chunks: list[dict[str, Any]] = []
    h3_tags = soup.find_all("h3")

    if not h3_tags:
        # Pas de h3 → fallback parser générique
        return _parse_generic_file(filepath, rel_path)

    for idx, h3 in enumerate(h3_tags):
        func_name_raw = h3.get_text(strip=True)

        # Normaliser : "Current Device" → "CurrentDevice", "Dated Identifier" → "DatedIdentifier"
        # Ces h3 contiennent le nom de fonction avec un espace typographique dans la doc GLIMS
        func_name_raw_normalized = re.sub(r"\s+", "", func_name_raw)

        # Ignorer les headers de navigation : trop courts, contiennent "MISPL", ou
        # ne ressemblent pas à un identifiant PascalCase (lettres/chiffres seulement)
        if len(func_name_raw) < 2:
            continue
        if not re.match(r"^[A-Za-z][A-Za-z0-9\s]+$", func_name_raw):
            continue
        # Ignorer les titres de section évidents
        if any(kw in func_name_raw for kw in ("MISPL", "Fonctions", "Function", "Syntax", "Note")):
            continue

        # Collecter contenu jusqu'au prochain h3
        content_nodes = []
        sibling = h3.next_sibling
        while sibling:
            if isinstance(sibling, Tag) and sibling.name == "h3":
                break
            content_nodes.append(sibling)
            sibling = sibling.next_sibling

        # Extraire description (premiers <p>)
        description_parts = []
        signature = ""
        return_type = ""
        func_name = func_name_raw_normalized  # espace supprimé : "Current Device" → "CurrentDevice"
        examples_parts = []

        def _process_node(inner: Any) -> None:
            """Traite un noeud HTML individuel — extrait description/signature/exemples."""
            nonlocal signature, return_type, func_name
            if not isinstance(inner, Tag):
                t = str(inner).strip()
                if t:
                    description_parts.append(t)
                return

            if inner.name == "blockquote":
                # Déplier le blockquote : traiter récursivement chaque enfant direct
                for child in inner.children:
                    _process_node(child)

            elif inner.name == "p":
                txt = _clean_text(inner.get_text())
                if txt:
                    description_parts.append(txt)

            elif inner.name == "table":
                sig, rt, fn = _extract_signature_from_table(inner)
                if sig:
                    signature = sig
                    return_type = rt
                    # N'écraser func_name que si le candidat est plus long ou plus précis
                    # que le nom issu du h3 — évite "Current" qui écrase "CurrentDevice"
                    if fn and re.match(r"^[A-Z][a-zA-Z0-9]+$", fn):
                        if len(fn) >= len(func_name):
                            func_name = fn

            elif inner.name in ("ul", "ol"):
                items = [_clean_text(li.get_text()) for li in inner.find_all("li")]
                examples_parts.extend(items)

            elif inner.name in ("pre", "code"):
                code_text = inner.get_text()
                if code_text.strip():
                    examples_parts.append(f"Exemple : {_clean_text(code_text)}")

            elif inner.name in ("h4", "h5"):
                subtitle = _clean_text(inner.get_text())
                if subtitle:
                    description_parts.append(f"\n{subtitle}")

        for node in content_nodes:
            _process_node(node)

        # Construire le texte du chunk avec structure explicite
        parts = [f"FONCTION : {func_name}"]
        if signature:
            parts.append(f"SIGNATURE : {signature}")
        if return_type:
            parts.append(f"TYPE DE RETOUR : {return_type}")
        if description_parts:
            parts.append("DESCRIPTION : " + " ".join(description_parts))
        if examples_parts:
            parts.append("EXEMPLES :\n" + "\n".join(f"  - {e}" for e in examples_parts[:5]))

        full_text = _clean_text("\n".join(parts))

        if len(full_text) < 40:
            continue

        # Si le chunk dépasse la limite → split mais garder signature intacte
        if len(full_text) > CHUNK_MAX_CHARS:
            sub_chunks = _split_preserving_signature(full_text, signature, CHUNK_MAX_CHARS)
            for j, sub in enumerate(sub_chunks):
                chunks.append(_make_chunk(
                    sub, doc_title, rel_path, idx * 100 + j,
                    func_name, func_name, return_type, signature,
                    "\n".join(examples_parts),
                ))
        else:
            chunks.append(_make_chunk(
                full_text, doc_title, rel_path, idx,
                func_name, func_name, return_type, signature,
                "\n".join(examples_parts),
            ))

        # Mini-chunks par valeur AttributeName (fix angle mort déterministe)
        if "Attribute" in func_name or "AttributeName" in " ".join(description_parts):
            desc_text = " ".join(description_parts)
            chunks.extend(_make_attribute_mini_chunks(
                func_name, doc_title, rel_path, idx,
                signature, return_type, desc_text,
            ))

    return chunks


def _make_attribute_mini_chunks(
    func_name: str,
    doc_title: str,
    rel_path: str,
    base_idx: int,
    signature: str,
    return_type: str,
    description_text: str,
) -> list[dict[str, Any]]:
    """
    Pour les fonctions avec paramètre AttributeName (Attribute, Order.Attribute, etc.),
    crée un mini-chunk par valeur d'attribut documentée.

    Résout l'angle mort déterministe : quand le chunk principal dépasse 1400 chars,
    les valeurs AttributeName en fin de liste (ex: "WorkPlaceCodeList", "ConsultResults")
    sont coupées → absentes du BM25 → exact-match impossible.

    Chaque mini-chunk porte : function_name + signature spécifique + description de la valeur.
    Coût : ~40-80 chunks supplémentaires pour toutes les fonctions Attribute.
    """
    mini_chunks: list[dict[str, Any]] = []

    # Détecter valeurs AttributeName : PascalCase terminant par List/CodeList/Flags/Info/Sequence
    # Le texte est extrait via get_text() → pas de guillemets, valeurs en PascalCase brut
    # Pattern élargi pour couvrir aussi "InputSpecimen", "Position", "NormalPosition"...
    attr_values_raw = re.findall(
        r'\b([A-Z][a-zA-Z0-9]*(?:List|CodeList|Flags|Info|Sequence|Specimen|Position|Time|Summary|Urgency|Comments?))\b',
        description_text
    )
    # Dédupliquer en préservant l'ordre
    seen: set[str] = set()
    attr_values = []
    for v in attr_values_raw:
        if v not in seen:
            seen.add(v)
            attr_values.append(v)

    if len(attr_values) < 3:  # pas une liste de valeurs AttributeName
        return []

    # Extraire descriptions par valeur depuis le texte (best-effort)
    # Format typique : "ValeurXxx" suivi de description jusqu'à la valeur suivante
    for i, val in enumerate(attr_values):
        # Chercher la description de cette valeur dans le texte
        pattern = re.escape(f'"{val}"') + r'[^"]*?([^"]{10,200})'
        m = re.search(pattern, description_text, re.DOTALL)
        desc = _clean_text(m.group(1)) if m else ""
        desc = desc[:200].split("\n")[0].strip()  # première ligne seulement

        mini_text = (
            f"FONCTION : {func_name} (table : {doc_title})\n"
            f"SIGNATURE : {func_name}(\"{val}\")\n"
            f"VALEUR ATTRIBUTENAME : \"{val}\"\n"
        )
        if desc:
            mini_text += f"DESCRIPTION : {desc}\n"
        mini_text = _clean_text(mini_text)

        if len(mini_text) < 30:
            continue

        specific_sig = f'{func_name}("{val}")'
        mini_chunks.append(_make_chunk(
            mini_text, doc_title, rel_path,
            base_idx * 1000 + i,
            f"{func_name}_{val}",  # section unique
            func_name,             # function_name → boosting BM25 intact
            return_type,
            specific_sig,
            "",
        ))

    return mini_chunks


def _split_preserving_signature(text: str, signature: str, max_chars: int) -> list[str]:
    """
    Découpe un texte long en préservant toujours la signature dans chaque sous-chunk.
    La signature est l'information la plus critique — ne jamais la perdre en split.
    """
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    sig_header = f"SIGNATURE : {signature}" if signature else ""

    for para in paragraphs:
        if current_len + len(para) > max_chars and current:
            chunk_text = "\n\n".join(current)
            chunks.append(chunk_text)
            # Overlap : réinjecter signature + derniers 400 chars
            overlap_seed = [sig_header] if sig_header and sig_header not in para else []
            tail = "\n\n".join(current)[-CHUNK_OVERLAP_CHARS:]
            current = overlap_seed + [tail, para] if tail != para else overlap_seed + [para]
            current_len = sum(len(c) for c in current)
        else:
            current.append(para)
            current_len += len(para)

    if current:
        chunks.append("\n\n".join(current))

    return chunks if chunks else [text[:max_chars]]


def _parse_generic_file(filepath: Path, rel_path: str) -> list[dict[str, Any]]:
    """
    Parser générique pour fichiers sans h3 (pages conceptuelles, ERD, syntaxe...).
    Découpe par h2/h4 ou, si absent, par blocs <p> de taille raisonnable.
    """
    html = _read_html(filepath)
    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.find("title") or soup.find("h1")
    doc_title = _clean_text(title_tag.get_text()) if title_tag else filepath.stem

    chunks: list[dict[str, Any]] = []
    headers = soup.find_all(["h2", "h4"])

    if headers:
        for idx, header in enumerate(headers):
            section_title = _clean_text(header.get_text())
            if not section_title:
                continue
            content_parts: list[str] = []
            sibling = header.next_sibling
            while sibling:
                if isinstance(sibling, Tag) and sibling.name in ("h2", "h4"):
                    break
                if isinstance(sibling, Tag):
                    t = _clean_text(sibling.get_text(separator=" "))
                    if t:
                        content_parts.append(t)
                elif str(sibling).strip():
                    content_parts.append(_clean_text(str(sibling)))
                sibling = sibling.next_sibling

            full_text = _clean_text(f"{section_title}\n" + "\n".join(content_parts))
            if len(full_text) < 60:
                continue

            # Détecter si section_title est un nom de fonction MISPL
            # Patterns : "Correspondent.SendMail()" / "SendMail" / "GetCorrespondent"
            # BLACKLIST : mots-clés UI/doc qui ne sont pas des fonctions
            _NOT_FUNCTIONS = {
                "MISPL", "Introduction", "Fonctions", "Functions", "Syntax", "Note",
                "Remarque", "Example", "Exemple", "Avertissement", "Warning",
                "Résultats", "Résultat", "Configuration", "Solution", "Champs",
                "Usage", "Historique", "History", "Annexe", "Appendix",
                "GLIMS", "Contexte", "Context", "Overview",
            }
            fn_match = re.match(
                r"^([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9]*)?)\s*\(?\)?$",
                section_title.strip()
            )
            extracted_fn = ""
            if fn_match:
                candidate = fn_match.group(1).replace(".", "")
                # Valider : PascalCase ou contient un point → fonction, et pas dans la blacklist
                if (re.match(r"^[A-Z][a-zA-Z0-9]+$", candidate) or "." in section_title) \
                        and candidate not in _NOT_FUNCTIONS:
                    extracted_fn = candidate
                    if extracted_fn:
                        KNOWN_FUNCTION_NAMES.add(extracted_fn)

            if len(full_text) > CHUNK_MAX_CHARS:
                for j, sub in enumerate(_split_preserving_signature(full_text, "", CHUNK_MAX_CHARS)):
                    chunks.append(_make_chunk(sub, doc_title, rel_path, idx * 100 + j,
                                              section_title, extracted_fn))
            else:
                chunks.append(_make_chunk(full_text, doc_title, rel_path, idx,
                                          section_title, extracted_fn))
    else:
        # Aucun header → chunk par blocs de paragraphes
        all_text = _clean_text(soup.get_text(separator="\n"))
        if len(all_text) > 100:
            for j, sub in enumerate(_split_preserving_signature(all_text, "", CHUNK_MAX_CHARS)):
                chunks.append(_make_chunk(sub, doc_title, rel_path, j, None))

    return chunks


# ── Parser reference_guide : extrait UNIQUEMENT la section MISPLFunctions ────

_REFERENCE_GUIDE_STEMS = {"ssit", "ord", "spmn"}

def _parse_reference_guide_file(filepath: Path, rel_path: str) -> list[dict[str, Any]]:
    """
    Parser pour les fichiers reference_guide (ssit.htm, ord.htm, spmn.htm, ...).
    Ces fichiers ont 3 sections : Fields | Menu functions | MISPL functions.
    On ne parse QUE la section ancre #MISPLFunctions pour éviter de polluer
    l'index avec les Menu functions (éléments UI, pas des fonctions MISPL appelables).
    """
    html_text = _read_html(filepath)
    soup = BeautifulSoup(html_text, "lxml")

    title_tag = soup.find("title") or soup.find("h1")
    # Extraire le vrai nom de table (ex: "SpecificSite" depuis "GLIMS reference guide - SpecificSite")
    raw_title = _clean_text(title_tag.get_text()) if title_tag else filepath.stem
    doc_title = raw_title.split(" - ")[-1].strip() if " - " in raw_title else raw_title

    chunks: list[dict[str, Any]] = []

    # Trouver l'ancre MISPLFunctions
    mispl_anchor = soup.find("a", attrs={"name": "MISPLFunctions"})
    if not mispl_anchor:
        return []  # pas de section MISPL dans ce fichier

    # Collecter tous les h3 APRÈS l'ancre MISPLFunctions
    # Stratégie : trouver le h2 "MISPL functions" puis parcourir les h3 jusqu'au prochain h2
    mispl_h2 = mispl_anchor.find_next("h2")
    if not mispl_h2:
        return []

    # Parcourir les siblings après le h2 MISPL jusqu'au prochain h2 (section "Enfants" ou "Children")
    func_h3_tags = []
    node = mispl_h2.next_sibling
    while node:
        if isinstance(node, Tag):
            if node.name == "h2":
                break  # fin de la section MISPL
            if node.name == "h3":
                func_h3_tags.append(node)
        node = node.next_sibling

    for idx, h3 in enumerate(func_h3_tags):
        func_name_raw = h3.get_text(strip=True)
        func_name = re.sub(r"\s+", "", func_name_raw)

        if len(func_name_raw) < 2:
            continue
        if not re.match(r"^[A-Za-z][A-Za-z0-9\s\xa0]+$", func_name_raw):
            continue

        # Collecter le contenu jusqu'au prochain h3
        content_nodes = []
        sibling = h3.next_sibling
        while sibling:
            if isinstance(sibling, Tag) and sibling.name == "h3":
                break
            content_nodes.append(sibling)
            sibling = sibling.next_sibling

        description_parts = []
        signature = ""
        return_type = ""
        examples_parts = []

        def _proc(inner: Any) -> None:
            nonlocal signature, return_type, func_name
            if not isinstance(inner, Tag):
                t = str(inner).strip()
                if t:
                    description_parts.append(t)
                return
            if inner.name == "p":
                cls = inner.get("class", [])
                if "Synopsis" in cls or "synopsis" in cls:
                    sig_text = _clean_text(inner.get_text(separator=" "))
                    if sig_text:
                        signature = sig_text
                        # Extraire le type de retour du début
                        m = re.match(r"^(\w+)\s+", sig_text)
                        if m and m.group(1) in MISPL_RETURN_TYPES | {"Void", "PositiveInteger", "PositiveFractional", "Logical"}:
                            return_type = m.group(1)
                else:
                    txt = _clean_text(inner.get_text())
                    if txt:
                        description_parts.append(txt)
            elif inner.name == "dl":
                for child in inner.children:
                    if isinstance(child, Tag):
                        if child.name in ("dt", "dd"):
                            t = _clean_text(child.get_text())
                            if t:
                                description_parts.append(t)
            elif inner.name == "div":
                for child in inner.children:
                    _proc(child)
            elif inner.name in ("pre", "code"):
                ct = inner.get_text().strip()
                if ct:
                    examples_parts.append(f"Exemple : {_clean_text(ct)}")

        for node in content_nodes:
            _proc(node)

        parts = [f"FONCTION : {func_name} (table : {doc_title})"]
        if signature:
            parts.append(f"SIGNATURE : {signature}")
        if return_type:
            parts.append(f"TYPE DE RETOUR : {return_type}")
        if description_parts:
            parts.append("DESCRIPTION : " + " ".join(description_parts))
        if examples_parts:
            parts.append("EXEMPLES :\n" + "\n".join(f"  - {e}" for e in examples_parts[:5]))

        full_text = _clean_text("\n".join(parts))
        if len(full_text) < 40:
            continue

        if len(full_text) > CHUNK_MAX_CHARS:
            for j, sub in enumerate(_split_preserving_signature(full_text, signature, CHUNK_MAX_CHARS)):
                chunks.append(_make_chunk(sub, doc_title, rel_path, idx * 100 + j,
                                          func_name, func_name, return_type, signature,
                                          "\n".join(examples_parts)))
        else:
            chunks.append(_make_chunk(full_text, doc_title, rel_path, idx,
                                      func_name, func_name, return_type, signature,
                                      "\n".join(examples_parts)))

        # Mini-chunks par valeur AttributeName (fix angle mort déterministe)
        if "Attribute" in func_name or "AttributeName" in " ".join(description_parts):
            desc_text = " ".join(description_parts)
            chunks.extend(_make_attribute_mini_chunks(
                func_name, doc_title, rel_path, idx,
                signature, return_type, desc_text,
            ))

    return chunks


# ── Routeur : choisir le bon parser selon le fichier ──────────────────────────

_FUNCTION_FILE_STEMS = {
    # Fonctions table-indépendantes
    "function_string", "function_datetime", "function_mathematical",
    "function_datatypeconversion", "function_miscellaneous",
    "function_interactive", "function_errormessages",
    "function_billing", "function_readingvariables", "function_writingvariables",
    # Fonctions table-spécifiques (Content/routine/*_m_*.htm)
    "orders_m_attribute", "orders_m_get_identifier", "orders_m_recalculate_specimen",
    "results_m_attribute", "results_m_workspecimen",
    "specimens_m_attribute", "specimens_m_add_request", "specimens_m_collection_info",
    "specimens_m_directparent", "specimens_m_result", "specimens_m_set_measured_size",
    "specimens_m_variables",
    # Fichiers avec fonctions h3 : SendMail (contient Correspondent.SendMail, User.SendMail, etc.)
    "mispl_send_mail",
    # Contexte non-conformités (h2 par fonction, contient RegisterNonconformity / GetNonconformity)
    "nc_mispl",
}

# Reference guide — utilise _parse_reference_guide_file (section MISPLFunctions seulement)
# Ne pas mettre dans _FUNCTION_FILE_STEMS pour éviter double-parsing
_REFERENCE_GUIDE_MISPL_STEMS = {
    # Tables déjà indexées
    "ssit", "ord", "spmn", "rslt", "actn",
    # Nouvelles tables ajoutées
    "crsp",   # Correspondent : Attribute, SendMail, Identification, HCCode, GroupMembership...
    "obj",    # Object : Age, AgeInDays, AgeInYears, AttributeList, AttributePeriod, Person, GetResult...
    "prsn",   # Person : GetMedicalRecord, BloodGroup, SendMail, Identification...
    "stn",    # Station : PrintLabels, GetPrinterId, Attribute...
    "prop",   # Property : GetResult, ResultFor, Attribute...
    "mat",    # Material : fonctions matériel
    "mcra",   # MicrobiologyAction : AddCarrier, Carrier, Isolation, GetIsolation...
    "isol",   # Isolation : Antibiogram, Organism, GetAntibiogram...
    "bbag",   # BloodBag : CreateOrder, Verify, fonctions transfusion
    "wlt",    # WorkList : fonctions listes de travail
    "rqst",   # Request : AddRequest, CancelRequest, Order, Specimen...
    "rprt",   # Report : fonctions comptes-rendus
    "usr",    # sc_User : SendMail, HasPrivilege, Department...
    "enct",   # Encounter : fonctions visites
    "dept",   # Department : fonctions disciplines
    "nc",     # Nonconformity : Type, Description, Register...
    "stay",   # Stay : fonctions séjours
    "diag",   # Diagnosis : Code, DiagnosisCode, System...
    # Nouvelles tables vérifiées (fonctions h3 réelles confirmées)
    "gsit",   # gp_Site : CurrentSessionHasPrivilege, AddLogEntry, Expand...
    "ptex",   # PathologyExam : 10 fonctions pathologie
    "os",     # ObjectStatus : 10 fonctions statuts objet
    "bsel",   # BloodSelection : 7 fonctions sélection sang
    "carr",   # Carrier : 5 fonctions plaques microbiologie
}


# Fichiers UI/doc généralistes qui polluent le RAG avec function_name parasite
# (détectés dans les logs : remontent en EXACT match sur requêtes MISPL)
_EXCLUDED_STEMS = {
    "shielding_routine_usage",       # UI protection données — pas de fonctions MISPL
    "attachments",                   # UI pièces jointes
    "order_entry_order_identifier_types",  # doc UI types identifiants
}


def parse_html_file(filepath: Path, rel_path: str) -> list[dict[str, Any]]:
    stem = filepath.stem.lower()
    rel = rel_path.replace("\\", "/")
    # Exclure les répertoires UI/modules sans fonctions MISPL
    if "modules/genetics" in rel or "modules/genetics" in rel.lower():
        return []
    # Exclure les fichiers UI parasites identifiés dans les logs
    if stem in _EXCLUDED_STEMS:
        return []
    # Reference guide priority : parser spécialisé section MISPLFunctions uniquement
    if stem in _REFERENCE_GUIDE_MISPL_STEMS:
        return _parse_reference_guide_file(filepath, rel_path)
    if any(fn in stem for fn in _FUNCTION_FILE_STEMS):
        return _parse_function_file(filepath, rel_path)
    return _parse_generic_file(filepath, rel_path)


# ── Build principal ────────────────────────────────────────────────────────────

def build_vectorstore(use_openai: bool = False, rebuild: bool = True) -> None:
    print(f"\n{'='*60}")
    print("MISPL RAG — Build Vectorstore v2")
    print(f"{'='*60}")
    print(f"Docs root : {DOCS_ROOT}")

    htm_files = sorted(DOCS_ROOT.rglob("*.htm"))
    print(f"Fichiers HTML trouvés : {len(htm_files)}")

    # Embedding
    if use_openai:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("OPENAI_API_KEY manquant")
        ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=api_key, model_name="text-embedding-3-small"
        )
        embed_model = "openai/text-embedding-3-small"
    else:
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        embed_model = "local/paraphrase-multilingual-MiniLM-L12-v2"
    print(f"Embedding : {embed_model}")

    # ChromaDB
    VECTORSTORE_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(VECTORSTORE_PATH))

    if rebuild:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"Collection '{COLLECTION_NAME}' supprimée (rebuild)")
        except Exception:
            pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    # Chunking
    all_chunks: list[dict[str, Any]] = []
    skipped = 0
    for htm_path in tqdm(htm_files, desc="Parsing HTML"):
        rel_path = str(htm_path.relative_to(DOCS_ROOT.parent)).replace("\\", "/")
        try:
            chunks = parse_html_file(htm_path, rel_path)
            all_chunks.extend(chunks)
        except Exception as e:
            tqdm.write(f"  [WARN] {rel_path}: {e}")
            skipped += 1

    print(f"\nChunks générés : {len(all_chunks)} (fichiers ignorés : {skipped})")
    print(f"Fonctions MISPL indexées : {len(KNOWN_FUNCTION_NAMES)}")

    # Ingestion ChromaDB par batch
    BATCH = 500
    for i in tqdm(range(0, len(all_chunks), BATCH), desc="Ingestion ChromaDB"):
        batch = all_chunks[i: i + BATCH]
        collection.add(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[c["metadata"] for c in batch],
        )

    # Sauvegarder corpus BM25 (textes + function_name pour index exact-match)
    BM25_CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    bm25_data = {
        "chunks": [
            {
                "id": c["id"],
                "text": c["text"],
                "function_name": c["metadata"].get("function_name", ""),
                "source": c["metadata"].get("source", ""),
                "section": c["metadata"].get("section", ""),
                "return_type": c["metadata"].get("return_type", ""),
                "signature": c["metadata"].get("signature", ""),
                "category": c["metadata"].get("category", ""),
                "priority": c["metadata"].get("priority", False),
                "has_examples": c["metadata"].get("has_examples", False),
            }
            for c in all_chunks
        ],
        "known_functions": sorted(KNOWN_FUNCTION_NAMES),
    }
    with open(BM25_CORPUS_PATH, "w", encoding="utf-8") as f:
        json.dump(bm25_data, f, ensure_ascii=False, indent=2)

    # Manifest
    manifest = {
        "total_chunks": len(all_chunks),
        "total_files": len(htm_files),
        "skipped_files": skipped,
        "known_functions_count": len(KNOWN_FUNCTION_NAMES),
        "embedding_model": embed_model,
        "collection": COLLECTION_NAME,
        "vectorstore_path": str(VECTORSTORE_PATH),
        "bm25_corpus_path": str(BM25_CORPUS_PATH),
    }
    manifest_path = VECTORSTORE_PATH.parent / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Vectorstore construit")
    print(f"   Chunks : {len(all_chunks)}")
    print(f"   Fonctions MISPL connues : {len(KNOWN_FUNCTION_NAMES)}")
    print(f"   Corpus BM25 : {BM25_CORPUS_PATH}")
    print(f"   Manifest : {manifest_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build GLIMS MISPL vectorstore v2")
    parser.add_argument("--openai", action="store_true", help="OpenAI embeddings")
    parser.add_argument("--no-rebuild", action="store_true", help="Ne pas recréer la collection")
    args = parser.parse_args()
    build_vectorstore(use_openai=args.openai, rebuild=not args.no_rebuild)
