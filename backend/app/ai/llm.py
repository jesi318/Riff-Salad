"""
LocalOllamaLLMService
Generates tags, descriptions, and parses natural-language search intent.
All inference is local via Ollama. Never hard-codes a model name.
"""
import json
import re
from app.core.config import LLM_MODEL


class LLMService:
    def generate_tags_and_description(self, context: dict) -> dict:
        raise NotImplementedError

    def parse_search_intent(self, query: str) -> dict:
        raise NotImplementedError


# ── Synonym / concept normalization table ─────────────────────────────────────
# Maps natural-language words/phrases → structured musical properties.
# Applied BEFORE LLM to constrain hallucination surface and give deterministic
# results for common music vocabulary.
_TEMPO_SYNONYMS: list[tuple[str, tuple]] = [
    # Fast
    ("fast picking", ("bpm_min", 130)),
    ("frantic",      ("bpm_min", 150)),
    ("blast beat",   ("bpm_min", 160)),
    ("rapid",        ("bpm_min", 130)),
    ("speedy",       ("bpm_min", 130)),
    ("upbeat",       ("bpm_min", 120)),
    ("uptempo",      ("bpm_min", 120)),
    ("up-tempo",     ("bpm_min", 120)),
    ("quick",        ("bpm_min", 120)),
    ("fast",         ("bpm_min", 120)),
    # Slow
    ("heavy slow",   ("bpm_max", 85)),
    ("doom metal",   ("bpm_max", 80)),
    ("doomy",        ("bpm_max", 80)),
    ("doom",         ("bpm_max", 80)),
    ("plodding",     ("bpm_max", 80)),
    ("sluggish",     ("bpm_max", 90)),
    ("slow",         ("bpm_max", 95)),
    # Mid
    ("mid-tempo",    ("bpm_range", (90, 115))),
    ("mid tempo",    ("bpm_range", (90, 115))),
    ("midtempo",     ("bpm_range", (90, 115))),
    ("medium tempo", ("bpm_range", (90, 115))),
    ("groovy",       ("bpm_range", (80, 130))),
    ("medium",       ("bpm_range", (88, 120))),
]

_ENERGY_SYNONYMS: list[tuple[str, tuple]] = [
    # High energy — order matters, longer phrases first
    ("palm-muted",   ("energy_min", 0.06)),
    ("palm muted",   ("energy_min", 0.06)),
    ("palm mute",    ("energy_min", 0.06)),
    ("crushing",     ("energy_min", 0.13)),
    ("brutal",       ("energy_min", 0.13)),
    ("aggressive",   ("energy_min", 0.10)),
    ("intense",      ("energy_min", 0.10)),
    ("chugging",     ("energy_min", 0.08)),
    ("chunky",       ("energy_min", 0.08)),
    ("distorted",    ("energy_min", 0.08)),
    ("heavy",        ("energy_min", 0.08)),
    ("loud",         ("energy_min", 0.08)),
    # Low energy
    ("fingerpicking", ("energy_max", 0.07)),
    ("finger picking", ("energy_max", 0.07)),
    ("fingerstyle",  ("energy_max", 0.07)),
    ("delicate",     ("energy_max", 0.05)),
    ("ambient",      ("energy_max", 0.05)),
    ("gentle",       ("energy_max", 0.05)),
    ("mellow",       ("energy_max", 0.07)),
    ("soft",         ("energy_max", 0.06)),
    ("quiet",        ("energy_max", 0.06)),
    ("clean",        ("energy_max", 0.07)),
]

_DENSITY_SYNONYMS: list[tuple[str, tuple]] = [
    # High density
    ("tapping",      ("density_min", 4.0)),
    ("many notes",   ("density_min", 3.0)),
    ("shredding",    ("density_min", 3.5)),
    ("shred",        ("density_min", 2.5)),
    ("busy",         ("density_min", 3.0)),
    ("dense",        ("density_min", 3.0)),
    # Low density
    ("open chord",   ("density_max", 1.5)),
    ("open chords",  ("density_max", 1.5)),
    ("held chord",   ("density_max", 1.5)),
    ("held chords",  ("density_max", 1.5)),
    ("minimal",      ("density_max", 1.5)),
    ("sparse",       ("density_max", 1.5)),
    ("simple",       ("density_max", 2.0)),
]

_MOOD_TO_MODE: list[tuple[str, str]] = [
    ("sinister",      "minor"),
    ("melancholic",   "minor"),
    ("dark sounding", "minor"),
    ("dark",          "minor"),
    ("moody",         "minor"),
    ("sad",           "minor"),
    ("uplifting",     "major"),
    ("joyful",        "major"),
    ("happy",         "major"),
    ("bright",        "major"),
]


def _apply_synonym_table(q_lower: str, filters: dict) -> dict:
    """
    Fast pass over the synonym tables. Multi-word phrases are listed
    first in each table so they take priority.
    """
    all_tempo = sorted(_TEMPO_SYNONYMS, key=lambda x: len(x[0]), reverse=True)
    for phrase, (key, val) in all_tempo:
        if phrase in q_lower:
            if key == "bpm_range":
                filters.setdefault("bpm_min", val[0])
                filters.setdefault("bpm_max", val[1])
            elif key == "bpm_min":
                existing = filters.get("bpm_min", 0)
                filters["bpm_min"] = max(existing, int(val))
            elif key == "bpm_max":
                existing = filters.get("bpm_max", 9999)
                filters["bpm_max"] = min(existing, int(val))

    all_energy = sorted(_ENERGY_SYNONYMS, key=lambda x: len(x[0]), reverse=True)
    for phrase, (key, val) in all_energy:
        if phrase in q_lower:
            filters.setdefault(key, val)

    all_density = sorted(_DENSITY_SYNONYMS, key=lambda x: len(x[0]), reverse=True)
    for phrase, (key, val) in all_density:
        if phrase in q_lower:
            filters.setdefault(key, val)

    all_mood = sorted(_MOOD_TO_MODE, key=lambda x: len(x[0]), reverse=True)
    for phrase, mode in all_mood:
        if phrase in q_lower:
            filters.setdefault("key_mode", mode)
            break


    return filters


class LocalOllamaService(LLMService):

    def _chat(self, prompt: str, temperature: float = 0.3) -> str:
        try:
            import ollama
            response = ollama.chat(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": temperature},
            )
            return response["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"Ollama error: {e}")

    def generate_tags_and_description(self, context: dict) -> dict:
        """
        Given concrete audio analysis facts, generate specific tags and
        a short description. Uses all numeric values so each riff gets
        differentiated output.
        """
        bpm           = context.get("bpm")
        key           = context.get("key", "unknown")
        energy        = context.get("energy", 0)
        onset_density = context.get("onset_density", 0)
        transcript    = (context.get("voice_note_transcript") or "").strip()
        user_notes    = (context.get("user_notes") or "").strip()

        bpm_str = f"{bpm:.1f} BPM" if bpm else "unknown BPM"
        if bpm:
            if bpm < 70:    tempo_feel = "very slow, doom-like"
            elif bpm < 90:  tempo_feel = "slow, heavy"
            elif bpm < 110: tempo_feel = "mid-tempo"
            elif bpm < 130: tempo_feel = "uptempo, driving"
            elif bpm < 160: tempo_feel = "fast, aggressive"
            else:           tempo_feel = "very fast, frantic"
        else:
            tempo_feel = "unknown tempo"

        if energy > 0.15:     energy_feel = "very high energy, loud, heavy"
        elif energy > 0.08:   energy_feel = "high energy"
        elif energy > 0.04:   energy_feel = "moderate energy"
        else:                 energy_feel = "low energy, quiet, delicate"

        if onset_density > 5:     density_feel = "extremely dense, shredding, many notes"
        elif onset_density > 3:   density_feel = "dense, busy playing"
        elif onset_density > 1.5: density_feel = "moderate note density"
        else:                     density_feel = "sparse, slow, few notes, held chords"

        key_lower = key.lower() if key else ""
        if "minor" in key_lower:
            key_mood = f"{key} — minor key, darker mood"
        elif "major" in key_lower:
            key_mood = f"{key} — major key, brighter sound"
        else:
            key_mood = key or "unknown key"

        prompt = f"""You are an expert guitar music tagger. A guitarist recorded this riff and the audio was analyzed. Your task is to produce SPECIFIC, ACCURATE tags and a description that distinguish this riff from others.

MEASURED audio data (not guesses):
- Tempo: {bpm_str} ({tempo_feel})
- Key: {key_mood}
- Energy level (RMS): {energy:.4f} ({energy_feel})
- Note density (onsets/sec): {onset_density:.2f} ({density_feel})
{f'- Guitarist voice note: "{transcript}"' if transcript else ""}
{f'- Guitarist manual notes: "{user_notes}"' if user_notes else ""}

Instructions:
1. Generate 5-8 SPECIFIC tags that accurately describe THIS riff. Tags should include tempo descriptor, genre/style, key/mood, and playing style. Do NOT repeat similar tags.
2. Write a single description sentence (max 25 words) that is SPECIFIC to this riff's character — mention the tempo, key, and distinctive quality. Do NOT write a generic description.

Bad example (too generic): {{"tags": ["rock", "electric", "power"], "description": "A powerful electric rock riff."}}
Good example for a 143 BPM E Major riff: {{"tags": ["fast", "143-bpm", "e-major", "aggressive", "high-energy"], "description": "An aggressive 143 BPM E Major riff with dense picking and very high energy."}}
Good example for a 99 BPM E Major riff: {{"tags": ["mid-tempo", "99-bpm", "e-major", "lead", "shredding"], "description": "A mid-tempo 99 BPM E Major lead guitar riff with dense shredding."}}

IMPORTANT: Always include the exact BPM value in both the tags (as a tag like "143-bpm") and the description sentence. This is the most important differentiator.

Respond with raw JSON only. No markdown, no explanation.
{{"tags": [...], "description": "..."}}"""

        raw = self._chat(prompt)
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            raw = match.group(0)
        try:
            data = json.loads(raw)
            tags = [str(t).lower().strip() for t in data.get("tags", [])[:10]]
            description = str(data.get("description", "")).strip()
            return {"tags": tags, "description": description}
        except Exception:
            return {"tags": [], "description": ""}

    def parse_search_intent(self, query: str) -> dict:
        """
        Converts a natural-language query into structured search filters.

        Strategy (layered, most reliable first):
        1. Deterministic regex for explicit numeric values (BPM, key notation).
        2. Synonym table — prevents slow/fast conflation, handles music vocabulary.
        3. LLM only for residual ambiguous intent.
        """
        filters: dict = {}
        q_lower = query.lower().strip()

        # ── Step 1: Deterministic regex ───────────────────────────────────────
        bpm_range_match = re.search(r'(\d+)\s*[-–to]+\s*(\d+)\s*bpm', q_lower)
        if bpm_range_match:
            filters['bpm_min'] = int(bpm_range_match.group(1)) - 5
            filters['bpm_max'] = int(bpm_range_match.group(2)) + 5

        if 'bpm_min' not in filters:
            bpm_match = re.search(
                r'(?:around|~|about|approx\.?)?\s*(\d{2,3})\s*bpm', q_lower
            )
            if bpm_match:
                bpm = int(bpm_match.group(1))
                fuzzy = any(w in q_lower for w in ('around', '~', 'about'))
                tolerance = 15 if fuzzy else 8
                filters['bpm_min'] = bpm - tolerance
                filters['bpm_max'] = bpm + tolerance

        # Key regex — negative lookahead avoids matching "b" in "bpm"
        key_match = re.search(
            r'\b([a-g])\s*(flat|sharp|#|b(?!pm))?\s*(major|minor|maj|min)\b',
            q_lower,
        )
        if key_match:
            note = key_match.group(1).upper()
            acc = key_match.group(2)
            if acc in ['flat', 'b']:    note += 'b'
            elif acc in ['sharp', '#']: note += '#'
            mode = "Major" if key_match.group(3).startswith('maj') else "Minor"
            filters['key'] = f"{note} {mode}"

        # ── Step 2: Synonym table expansion ──────────────────────────────────
        filters = _apply_synonym_table(q_lower, filters)

        # ── Step 3: LLM for residual intent ──────────────────────────────────
        _noise = {
            "riff", "riffs", "guitar", "something", "find", "give", "me",
            "show", "that", "are", "with", "and", "but", "not", "in", "of",
            "my", "any", "some", "a", "an", "the", "have", "got", "get",
            "for", "like", "want", "looking",
        }
        meaningful = [
            w for w in re.findall(r'\b\w+\b', q_lower)
            if w not in _noise and len(w) > 2
        ]
        # Only call LLM when meaningful unresolved words remain AND we have
        # no structural anchors yet (key or BPM from regex/synonym table).
        # Having a key is already a good structural anchor — don't over-call.
        has_anchor = "key" in filters or "bpm_min" in filters or "bpm_max" in filters
        if meaningful and not has_anchor and len(filters) < 2:
            try:
                llm_filters = self._llm_extract_filters(query, filters)
                # LLM fills gaps; deterministic values take precedence
                for k, v in llm_filters.items():
                    if k not in filters:
                        filters[k] = v
            except Exception as e:
                print(f"[search] LLM filter extraction skipped: {e}")

        print(f"[search] parse_search_intent result: {filters}")
        return filters

    def _llm_extract_filters(self, query: str, existing: dict) -> dict:
        """Ask the LLM to extract any remaining structured filters."""
        already = json.dumps(existing) if existing else "{}"
        prompt = f"""You are a music search filter extractor for a guitar riff app.

Extract structured search filters from this query: "{query}"

Already extracted by deterministic rules (do NOT re-derive these): {already}

Return ONLY a raw JSON object for what you can CONFIDENTLY extract that is NOT already in the above.
Available output keys (omit any you are not certain about):
- "bpm_min": integer minimum BPM
- "bpm_max": integer maximum BPM
- "key": string like "E Minor" or "G Major" (ONLY if a specific note letter is explicitly in the query)
- "key_mode": "minor" or "major" (ONLY if a mood word implies key mode — e.g. "dark" → minor)
- "energy_min": float 0.0-0.3 (ONLY if query explicitly says heavy/loud/distorted/aggressive/brutal)
- "energy_max": float 0.0-0.3 (ONLY if query explicitly says quiet/soft/clean/mellow/gentle)
- "density_min": float (ONLY if query explicitly says busy/dense/shredding/many notes/fast picking)
- "density_max": float (ONLY if query explicitly says sparse/minimal/simple/few notes)
- "text_hint": string for genre/style that doesn't map to the above (e.g. "blues", "jazz", "metal")

HARD RULES — violating these produces wrong results:
- "slow" means low BPM (bpm_max ≤ 95). "fast" means high BPM (bpm_min ≥ 120). NEVER confuse them.
- Only set energy_min/max if the query EXPLICITLY mentions volume or distortion, NOT implied by tempo.
- Only set density_min/max if the query EXPLICITLY mentions note density or playing style.
- If the query is vague or you're guessing, return {{}} (empty object).

Raw JSON only:"""

        raw = self._chat(prompt, temperature=0.1)
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            raw = match.group(0)
        try:
            data = json.loads(raw)
            result: dict = {}
            for k in ("bpm_min", "bpm_max", "energy_min", "energy_max",
                      "density_min", "density_max"):
                if k in data:
                    try:
                        result[k] = float(data[k])
                    except (TypeError, ValueError):
                        pass
            for k in ("key", "key_mode", "text_hint"):
                if k in data and isinstance(data[k], str) and data[k].strip():
                    result[k] = data[k].strip()
            return result
        except Exception:
            return {}


def get_llm_service() -> LLMService:
    return LocalOllamaService()
