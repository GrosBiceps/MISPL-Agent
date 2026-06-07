"""Inspect exact HTML structure around problematic h3 tags."""
import sys, re
sys.path.insert(0, r"C:\Users\Florian Travail\Documents\MISPL Agent\MISPL")
from pathlib import Path
from bs4 import BeautifulSoup
from src.rag.build_vectorstore import _read_html

base = Path(r"C:\Users\Florian Travail\Documents\MISPL Agent\MISPL\french\Content\configuration\mispl_texts\mispl_table_independent")

print("=" * 70)
print("function_datatypeconversion.htm — h3 tags")
print("=" * 70)
html = _read_html(base / "function_datatypeconversion.htm")
soup = BeautifulSoup(html, "lxml")
for h3 in soup.find_all("h3"):
    print(f"  h3 text: {repr(h3.get_text(strip=True)[:80])}")

print()
print("=" * 70)
print("function_miscellaneous.htm — h3 tags")
print("=" * 70)
html = _read_html(base / "function_miscellaneous.htm")
soup = BeautifulSoup(html, "lxml")
for h3 in soup.find_all("h3"):
    txt = h3.get_text(strip=True)
    print(f"  h3 text: {repr(txt[:80])}")
    if txt in ("Current Device", "Current Terminal", "Dated Identifier"):
        print(f"    -> raw HTML: {str(h3)[:200]}")
        # Regarder le sibling immédiat
        sib = h3.next_sibling
        for _ in range(3):
            if sib:
                print(f"    sibling: {str(sib)[:150]}")
                sib = sib.next_sibling
