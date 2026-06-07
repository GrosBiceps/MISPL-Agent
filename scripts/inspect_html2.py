"""Find where 'Directive' h3 comes from and why Current/Dated still wrong."""
import sys
sys.path.insert(0, r"C:\Users\Florian Travail\Documents\MISPL Agent\MISPL")
from pathlib import Path
from bs4 import BeautifulSoup
from src.rag.build_vectorstore import _read_html

base = Path(r"C:\Users\Florian Travail\Documents\MISPL Agent\MISPL\french\Content\configuration\mispl_texts\mispl_table_independent")

# 1. Trouver le h3 "Directive" dans datatypeconversion
print("=== datatypeconversion : ALL h3 including nested ===")
html = _read_html(base / "function_datatypeconversion.htm")
soup = BeautifulSoup(html, "lxml")
for h3 in soup.find_all("h3"):
    txt = h3.get_text(strip=True)
    parent = h3.parent.name if h3.parent else "?"
    print(f"  [{parent}] h3: {repr(txt[:60])}")

print()
print("=== FractionalToString h3 siblings (first 5) ===")
for h3 in soup.find_all("h3"):
    if "FractionalToString" in h3.get_text():
        sib = h3.next_sibling
        for i in range(8):
            if sib is None: break
            from bs4 import Tag
            if isinstance(sib, Tag):
                print(f"  [{sib.name}] {str(sib)[:120]}")
            sib = sib.next_sibling
        break

print()
print("=== miscellaneous : CurrentDevice h3 then signature ===")
html2 = _read_html(base / "function_miscellaneous.htm")
soup2 = BeautifulSoup(html2, "lxml")
for h3 in soup2.find_all("h3"):
    if h3.get_text(strip=True) in ("CurrentDevice", "DatedIdentifier"):
        print(f"h3 text: {repr(h3.get_text(strip=True))}")
        sib = h3.next_sibling
        for i in range(6):
            if sib is None: break
            from bs4 import Tag
            if isinstance(sib, Tag):
                print(f"  [{sib.name}] {str(sib)[:200]}")
                if sib.name == "blockquote":
                    for child in sib.children:
                        if isinstance(child, Tag):
                            print(f"    [{child.name}] {str(child)[:180]}")
            sib = sib.next_sibling
        print()
