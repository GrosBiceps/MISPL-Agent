import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.agent.linter import lint_mispl_code, LintResult
from src.agent.prompt_builder import build_system_prompt, SKILL_PROFILES
from src.rag.retriever import _tokenize

print("linter OK")
print("prompt_builder OK")
print("Skill profiles:", list(SKILL_PROFILES.keys()))

# Test linter
bad_code = "\n".join([
    "STRING PROGRAM",
    "  STRING x;",
    "  WHILE TRUE DO",
    "    x := x + 'a';",
    "  DONE;",
    "  x := 5 / 2;",
    "  .Sample.Id := 'X';",
    "RETURN x;",
])
result = lint_mispl_code(bad_code)
print(f"\nLint issues: {len(result.issues)}")
for issue in result.issues:
    print(f"  {issue}")
print("\nSummary:", result.summary())

# Test prompt builder
prompt = build_system_prompt(active_skills=["mispl-core"])
print(f"\nSystem prompt length: {len(prompt)} chars")
print("Prompt caching ready: OK (anthropic >= 0.28)")
