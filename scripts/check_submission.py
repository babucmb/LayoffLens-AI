from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
required = ["README.md", ".env.example", "backend/app/main.py", "backend/app/agent_runtime.py", "frontend/index.html", "docs/demo-script-3min.md", "docs/meta-api-integration.md", "docs/implementation-log.md", "docs/AGENT_ARCHITECTURE_TRANSFORMATION.md"]
missing = [p for p in required if not (root / p).exists()]
if missing:
    print("Missing:", ", ".join(missing))
    sys.exit(1)
text = "\n".join(p.read_text(encoding="utf-8") for p in [root / "README.md", root / "frontend/index.html"])
if "SYNTHETIC" not in text or "Demo fallback" not in text:
    print("Missing synthetic/demo disclosure")
    sys.exit(1)
if re.search(r"(sk-[A-Za-z0-9]{20,}|MODEL_API_KEY\s*=\s*[^\s<]+)", text):
    print("Possible secret leak")
    sys.exit(1)
print(f"Submission checks passed: {len(required)} required paths, disclosures present, no obvious key leak.")
