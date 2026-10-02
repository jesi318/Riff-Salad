import re, json
from app.ai.llm import LocalOllamaService
llm = LocalOllamaService()

def test_query(query):
    prompt = f"""You are a search intent parser for a guitar riff library.
Convert the user's natural language search into structured database filters.

Allowed filters (ALL OPTIONAL, use only if strongly implied):
- "bpm_min": integer (minimum tempo)
- "bpm_max": integer (maximum tempo)
- "key": string (musical key, e.g. "E Major", "D Minor", "A Minor")

STRICT RULES:
- "fast" or "upbeat" implies "bpm_min": 120
- "slow" or "doom" implies "bpm_max": 95
- "mid-tempo" implies "bpm_min": 90, "bpm_max": 115
- If a specific BPM is mentioned (e.g. "around 100"), use +/- 15 BPM.
- Only extract hard facts. Leave stylistic words to the semantic engine.
- Return ONLY raw JSON.

Query: "{query}"

Examples:
"fast heavy riff" -> {{"bpm_min": 120}}
"slow mellow D minor" -> {{"bpm_max": 95, "key": "D Minor"}}
"shredding around 140 bpm" -> {{"bpm_min": 125, "bpm_max": 155}}
"""
    raw = llm._chat(prompt)
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match: raw = match.group(0)
    print(f"Q: {query:<30} -> {raw}")

for q in ["fast", "slow", "heavy riff around 100 bpm", "slow D minor", "fast aggressive"]:
    test_query(q)
