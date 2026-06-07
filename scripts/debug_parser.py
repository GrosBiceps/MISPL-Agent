import sys
sys.path.insert(0, r"C:\Users\Florian Travail\Documents\MISPL Agent\MISPL")
from pathlib import Path
from src.rag.build_vectorstore import _parse_function_file, KNOWN_FUNCTION_NAMES

base = Path(r"C:\Users\Florian Travail\Documents\MISPL Agent\MISPL\french\Content\configuration\mispl_texts\mispl_table_independent")

BAD_NAMES = {"Directive", "Current", ""}

for fname in ["function_datatypeconversion.htm", "function_miscellaneous.htm"]:
    path = base / fname
    KNOWN_FUNCTION_NAMES.clear()
    chunks = _parse_function_file(path, str(path))
    print(f"\n=== {fname} ===")
    for c in chunks:
        fn = c["metadata"]["function_name"]
        sig = c["metadata"]["signature"]
        print(f"  [{fn}] sig={sig[:60] if sig else '(vide)'}")
        if fn in BAD_NAMES:
            print(f"    TEXT: {c['text'][:200]}")
