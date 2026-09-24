"""Tests des logiques de retrieval introduites en r2 (2026-09-24) :
déclencheurs d'expansion par mots entiers, candidats d'expansion non épinglés,
sélection finale (diversité, blocs sans fonction), éclatement des sections
multi-fonctions et mots-clés à l'ingestion."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import src.rag.retriever as retriever_mod
from src.rag.ingest_knowledge_base import (
    _extract_section_metadata,
    _keywords_for,
    _load_keywords,
    _split_multi_function_title,
)
from src.rag.retriever import (
    MISPLRetriever,
    _expansion_functions,
    _fuzzy_trigger_match,
    _max_non_function_docs,
    _select_final,
)


def _doc(doc_id, fn="", section="", **kw):
    return {"id": doc_id, "text": doc_id, "score": 0.5, "function_name": fn,
            "section": section or fn or doc_id, "category": "misc", "has_examples": False, **kw}


# ── Déclencheurs d'expansion ──────────────────────────────────────────────────

class TestTriggerMatch:
    def test_whole_word_match_and_plural(self):
        assert _fuzzy_trigger_match("plaque", "ensemencer une plaque de gelose")
        assert _fuzzy_trigger_match("plaque", "compter les plaques")

    def test_no_match_inside_longer_word(self):
        # « plaque » ne doit pas matcher « plaquettes » (score FIB-4)
        assert not _fuzzy_trigger_match("plaque", "age x asat / plaquettes")
        assert not _fuzzy_trigger_match("label", "le libelle d une analyse")

    def test_fuzzy_prefix_tolerates_short_suffix_only(self):
        assert _fuzzy_trigger_match("arrondir", "arrondis la valeur")
        assert not _fuzzy_trigger_match("stockage", "stockagexxxxxx")

    def test_multiword_trigger_has_no_fuzzy(self):
        assert not _fuzzy_trigger_match("extraire ipp", "extraire une sous chaine")

    def test_trigger_with_trailing_space_and_symbols(self):
        assert _fuzzy_trigger_match("abs ", "valeur abs de x")
        assert _fuzzy_trigger_match("hb <", "si hb < 10")


class TestExpansionFunctions:
    def test_order_of_appearance_and_qualifiers_ignored(self):
        known = {"Specimen", "AddCarriers", "Substr", "Len", "NumEntries"}
        assert _expansion_functions("Specimen.AddCarriers AddCarriers MediumMnemonicList", known) == ["AddCarriers"]
        assert _expansion_functions("Substr Substr Len NumEntries", known) == ["Substr", "Len", "NumEntries"]


# ── Sélection finale ──────────────────────────────────────────────────────────

class TestSelectFinal:
    def test_exact_docs_pinned_first(self):
        exact = [_doc("e1", "Substr", exact_match=True)]
        ranked = [_doc("a", "Len"), _doc("b", "Index")]
        out = _select_final(exact, ranked, 3)
        assert [d["id"] for d in out] == ["e1", "a", "b"]

    def test_one_doc_per_function_name(self):
        ranked = [_doc("s1", "Specimen"), _doc("s2", "Specimen"), _doc("s3", "Specimen"), _doc("r", "Round")]
        out = _select_final([], ranked, 2)
        assert [d["id"] for d in out] == ["s1", "r"]

    def test_group_siblings_deduplicated(self):
        ranked = [
            _doc("l", "Ltrim", group_section="Ltrim / Rtrim / Trim", source_file="s.md"),
            _doc("r", "Rtrim", group_section="Ltrim / Rtrim / Trim", source_file="s.md"),
            _doc("x", "Strip"),
        ]
        out = _select_final([], ranked, 2)
        assert [d["id"] for d in out] == ["l", "x"]

    def test_non_function_docs_capped_and_intro_deferred(self):
        ranked = [_doc("p1", section="Pattern 1"), _doc("intro", section="intro"),
                  _doc("p2", section="Pattern 2"), _doc("f1", "Today"), _doc("f2", "Now")]
        out = _select_final([], ranked, 4)
        ids = [d["id"] for d in out]
        assert ids[:3] == ["p1", "f1", "f2"]
        assert len(ids) == 4  # complété au second tour
        assert _max_non_function_docs(6) == 1 and _max_non_function_docs(10) == 2

    def test_backfill_when_not_enough_function_docs(self):
        ranked = [_doc("p1", section="Pattern 1"), _doc("p2", section="Pattern 2"), _doc("p3", section="Pattern 3")]
        assert len(_select_final([], ranked, 3)) == 3


# ── query() : expansion non épinglée ─────────────────────────────────────────

def _fake_retriever(dense_docs, known, exact_by_fn):
    retriever = object.__new__(MISPLRetriever)
    retriever.top_k = 6

    class _State:
        pass

    retriever._state = _State()
    retriever._state.known_functions = set(known)
    retriever._state.collection = MagicMock()
    retriever._state.collection.count.return_value = 1000
    retriever._dense_search = lambda q, n: [dict(d) for d in dense_docs]
    retriever._bm25_search = lambda q, n: []
    retriever._exact_match_search = lambda fn: [dict(d) for d in exact_by_fn.get(fn, [])]
    return retriever


class TestQueryExpansionNotPinned:
    def test_expansion_function_is_candidate_not_exact(self, monkeypatch):
        """« arrondir » déclenche l'expansion Round : la fiche Round entre dans
        le résultat mais sans exact_match ni score sentinelle 1.0."""
        round_doc = _doc("round", "Round", exact_match=True, score=1.0)
        retriever = _fake_retriever([_doc("other", "Abs")], {"Round", "Abs"}, {"Round": [round_doc]})
        monkeypatch.setattr(retriever_mod, "rerank",
                            lambda q, pool: [dict(d, score=0.3) for d in pool])
        out = retriever.query("comment arrondir une valeur", top_k=3)
        by_id = {d["id"]: d for d in out}
        assert "round" in by_id
        assert not by_id["round"]["exact_match"]
        assert max(d["score"] for d in out) < 1.0

    def test_verbatim_function_stays_exact_and_see_also_added(self, monkeypatch):
        cascade = _doc("cascade", "CascadeRequest", exact_match=True, score=1.0, see_also="AddRequest")
        add = _doc("add", "AddRequest", exact_match=True, score=1.0)
        retriever = _fake_retriever([], {"CascadeRequest", "AddRequest"},
                                    {"CascadeRequest": [cascade], "AddRequest": [add]})
        monkeypatch.setattr(retriever_mod, "rerank", lambda q, pool: list(pool))
        out = retriever.query("remplacer CascadeRequest", top_k=3)
        assert out[0]["id"] == "cascade" and out[0]["exact_match"]
        assert any(d["id"] == "add" and not d["exact_match"] for d in out)

    def test_extra_verbatim_names_need_compound_name(self):
        retriever = _fake_retriever([], {"NumericValue", "AddRequest", "Message"}, {})
        extras = retriever._detect_extra_function_names("Message avec NumericValue et AddRequest", "NumericValue")
        assert extras == ["AddRequest"]


# ── Ingestion ─────────────────────────────────────────────────────────────────

class TestIngestion:
    def test_split_multi_function_title(self):
        assert _split_multi_function_title("Ltrim / Rtrim / Trim") == ["Ltrim", "Rtrim", "Trim"]
        assert _split_multi_function_title("CreationTime / ReceiptTime (champs)") == ["CreationTime", "ReceiptTime"]
        assert _split_multi_function_title("ToLower / ToUpper [2]") == ["ToLower", "ToUpper"]
        assert _split_multi_function_title("Pattern 1 : Reflex test") == []
        assert _split_multi_function_title("Substr") == []

    def test_keywords_qualified_key_wins(self):
        kw = {"Attribute": "générique", "table_object/object_functions.md::Attribute": "objet"}
        assert _keywords_for("Attribute", "02_functions/table_object/object_functions.md", kw) == "objet"
        assert _keywords_for("Attribute", "02_functions/table_order/order_functions_extended.md", kw) == "générique"
        assert _keywords_for("", "x.md", kw) == ""

    def test_field_section_gets_function_name(self):
        meta = _extract_section_metadata("Sex (champ énuméré)", "## Sex (champ énuméré)\n**Type** : Enumerated", {})
        assert meta["function_name"] == "Sex"

    def test_keywords_file_is_valid(self):
        mots_cles, voir_aussi = _load_keywords()
        assert mots_cles, "rag_knowledge_base/mots_cles_fr.json doit exister et être non vide"
        assert all(isinstance(v, str) and v for v in mots_cles.values())
        assert all(isinstance(v, list) for v in voir_aussi.values())
