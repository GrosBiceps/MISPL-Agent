"""
Tests de validation de l'agent MISPL — questions de référence avec réponses attendues.
Ces tests vérifient que le RAG retrouve bien les bonnes fonctions MISPL.
Lancer : pytest tests/ -v
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Ces tests nécessitent le vectorstore construit — skip si absent
try:
    from src.rag.retriever import get_retriever
    VECTORSTORE_AVAILABLE = True
except Exception:
    VECTORSTORE_AVAILABLE = False


# ── Fixtures ────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def retriever():
    if not VECTORSTORE_AVAILABLE:
        pytest.skip("Vectorstore non construit — lancer build_vectorstore.py d'abord")
    return get_retriever(use_openai=False)


# ── Tests RAG — les bonnes fonctions doivent être retrouvées ────────────────────
class TestRAGRetrieval:
    """Vérifie que le RAG retrouve les bonnes sections pour les questions MISPL."""

    def test_string_functions_retrieved(self, retriever):
        """Substr, Index, Len doivent apparaître pour une question sur les chaînes."""
        docs = retriever.query("comment extraire une sous-chaîne en MISPL ?", top_k=5)
        sources = [d["source"] for d in docs]
        texts = " ".join([d["text"] for d in docs]).lower()
        assert any("function_string" in s for s in sources), "function_string.htm non retrouvé"
        assert "substr" in texts or "index" in texts, "Fonctions string non retrouvées dans les chunks"

    def test_date_functions_retrieved(self, retriever):
        """Today(), DateToString() doivent apparaître pour une question sur les dates."""
        docs = retriever.query("comment obtenir la date du jour en MISPL ?", top_k=5)
        texts = " ".join([d["text"] for d in docs]).lower()
        assert "today" in texts or "datetostring" in texts, "Fonctions date non retrouvées"

    def test_integer_conversion_retrieved(self, retriever):
        """IntegerToString doit apparaître pour une question sur la conversion."""
        docs = retriever.query("convertir un entier en chaîne de caractères MISPL", top_k=5)
        texts = " ".join([d["text"] for d in docs]).lower()
        assert "integertostring" in texts, "IntegerToString non retrouvé"

    def test_addlogentry_retrieved(self, retriever):
        """AddLogEntry doit apparaître pour une question sur les logs."""
        docs = retriever.query("écrire un log dans GLIMS depuis MISPL", top_k=5)
        texts = " ".join([d["text"] for d in docs]).lower()
        assert "addlogentry" in texts, "AddLogEntry non retrouvé"

    def test_currentuser_retrieved(self, retriever):
        """CurrentUser() doit apparaître pour une question sur l'utilisateur courant."""
        docs = retriever.query("récupérer le nom de l'utilisateur connecté GLIMS", top_k=5)
        texts = " ".join([d["text"] for d in docs]).lower()
        assert "currentuser" in texts, "CurrentUser non retrouvé"

    def test_math_functions_retrieved(self, retriever):
        """Round, Sqrt doivent apparaître pour les maths."""
        docs = retriever.query("fonctions mathématiques MISPL arrondi racine carrée", top_k=5)
        texts = " ".join([d["text"] for d in docs]).lower()
        assert "round" in texts or "sqrt" in texts, "Fonctions math non retrouvées"

    def test_score_quality(self, retriever):
        """Les scores de similarité doivent être raisonnables (> 0.3 pour une vraie question)."""
        docs = retriever.query("Substr extraire partie d'une chaîne", top_k=3)
        assert docs[0]["score"] > 0.3, f"Score trop bas : {docs[0]['score']:.3f}"


# ── Tests de syntaxe MISPL (ground truth manuel) ────────────────────────────────
class TestMISPLSyntaxExamples:
    """Exemples de code MISPL valide — sert de référence pour l'évaluation."""

    def test_string_program_structure(self):
        """Vérifie que nos exemples de référence ont la bonne structure."""
        valid_program = """STRING PROGRAM
  STRING result;
  result := "Hello";
RETURN result;"""
        assert "STRING PROGRAM" in valid_program
        assert "RETURN" in valid_program

    def test_integer_program_structure(self):
        valid_program = """INTEGER PROGRAM
  INTEGER val;
  val := 42;
RETURN val;"""
        assert "INTEGER PROGRAM" in valid_program

    def test_conditional_structure(self):
        valid_program = """LOGICAL PROGRAM
  INTEGER x;
  x := 5;
  IF x > 3 THEN
    RETURN TRUE;
  ELSE
    RETURN FALSE;
  ENDIF;
RETURN FALSE;"""
        assert "IF" in valid_program
        assert "ENDIF" in valid_program

    def test_while_structure(self):
        valid_program = """INTEGER PROGRAM
  INTEGER i, total;
  i := 1;
  total := 0;
  WHILE i <= 10 DO
    total := total + i;
    i := i + 1;
  DONE;
RETURN total;"""
        assert "WHILE" in valid_program
        assert "DONE" in valid_program
