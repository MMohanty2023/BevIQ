"""Small allowlisted project knowledge, separate from catalog and user uploads."""
from pathlib import Path
import re

from config import OLLAMA_MODEL, OLLAMA_VISION_MODEL, SQLITE_PATH

_GUIDE = Path(__file__).resolve().parents[1] / "docs" / "assistant-project-guide.md"


def is_project_question(query):
    text = query.lower().strip()
    # Real record/count requests keep the existing database route even if
    # the user adds 'in my project' or 'in BevIQ'.
    entity = bool(re.search(
        r"\b(?:brands?|products?|records?|supplier|beer|wine|rtd|spirits|master|upc|barcode|dataset)\b", text))
    if re.search(r"\b\d{10,14}\b|\b(?:id|identifier)\s*[:#-]?\s*[a-z0-9_-]+\b", text):
        return False
    explanatory = bool(re.search(
        r"\b(?:architecture|workflow|implementation|configuration|setup|deployment|working|logic|pipeline|source code|how does|how do|kaise|samjhao)\b", text
    )) or bool(re.match(
        r"^(?:(?:can|could|would)\s+you\s+)?(?:please\s+)?(?:explain|describe)\b", text
    ))
    data_action = bool(re.search(
        r"\b(?:show|list|find|search|compare|count|export|audit|check|verify|gino|dikhao|lookup|look up|missing|duplicates?)\b", text
    ))
    if entity and (
        re.search(r"\b(?:how many|kitne|kitni)\b", text)
        or (data_action and not explanatory)
    ):
        return False
    if re.fullmatch(r"(?:who are you|what can you do|what are your capabilities|help|features)[?.!]*", text):
        return True
    return bool(re.search(
        r"\b(?:beviq|pd comparison studio|"
        r"(?:this|my|our|the|mera|mere|apne|iss|is|ye|yeh)\s+(?:project|app|application|assistant)|"
        r"project\s+(?:architecture|setup|working|features|deployment))\b", text))


def get_project_context(query):
    # Never recursively index the repository, read .env, or include credentials.
    # Keep project context bounded so CPU generation does not ingest whole files.
    sources = ["config.py"]
    facts = (
        "Safe runtime configuration (not a live database-health result):\n"
        f"Text model: {OLLAMA_MODEL}\n"
        f"Vision model: {OLLAMA_VISION_MODEL}\n"
        f"SQLite fallback filename: {Path(SQLITE_PATH).name}\n"
        "Both local inference routes explicitly request CPU execution (num_gpu=0).\n"
        "MySQL is preferred when configured and reachable; SQLite is the fallback.\n"
        "Get actual counts and record details from database retrieval, not this guide.\n"
    )
    if _GUIDE.is_file():
        facts += "\nProject guide:\n" + _GUIDE.read_text(encoding="utf-8-sig")[:6500]
        sources.insert(0, "docs/assistant-project-guide.md")
    return {"text": facts, "source_files": sources}
