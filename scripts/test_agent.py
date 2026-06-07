"""Test complet pipeline agent : RAG + OpenRouter + linter."""
import sys, os
sys.path.insert(0, r"C:\Users\Florian Travail\Documents\MISPL Agent\MISPL")

from dotenv import load_dotenv
load_dotenv(r"C:\Users\Florian Travail\Documents\MISPL Agent\MISPL\.env")

print(f"API key set: {bool(os.environ.get('OPENROUTER_API_KEY'))}")

from src.agent.mispl_agent import ask_mispl, DEFAULT_MODEL

print(f"Modele: {DEFAULT_MODEL}")
print("Question: Comment utiliser Substr en MISPL ?")
print("-" * 60)

try:
    response = ask_mispl(
        "Comment utiliser la fonction Substr en MISPL pour extraire les 4 premiers caracteres ?",
        stream=False,
        save_session=False,
    )
    print(response[:1000])
    print("\n[OK] Pipeline complet fonctionne")
except Exception as e:
    print(f"[ERREUR] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
