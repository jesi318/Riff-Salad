"""
LocalOllamaLLMService
Generates tags, descriptions, and parses natural-language search intent.
All inference is local via Ollama.
Never hard-codes a model name — reads from config.
"""
import json
import re
from app.core.config import LLM_MODEL


class LLMService:
    def generate_tags_and_description(self, context: dict) -> dict:
        raise NotImplementedError

    def parse_search_intent(self, query: str) -> dict:
        raise NotImplementedError


class LocalOllamaService(LLMService):

    def _chat(self, prompt: str) -> str:
        try:
            import ollama
            response = ollama.chat(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.2},
            )
            return response["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"Ollama error: {e}")

    def generate_tags_and_description(self, context: dict) -> dict:
        """
        Given audio analysis facts, generate tags and a short description.
        Clearly marked as AI-generated estimates, not measured facts.
        """
        bpm       = context.get("bpm", "unknown")
        key       = context.get("key", "unknown")
        energy    = context.get("energy", 0)
        onset_den = context.get("onset_density", 0)
        transcript = context.get("voice_note_transcript", "")
        user_notes = context.get("user_notes", "")

        energy_word   = "high" if energy > 0.05 else "moderate" if energy > 0.01 else "low"
        density_word  = "dense" if onset_den > 4 else "moderate" if onset_den > 2 else "sparse"

        prompt = f"""You are a music metadata assistant. Based ONLY on the measured audio data below,
generate a JSON object with two keys: "tags" (an array of up to 8 short lowercase musical genre/style tags)
and "description" (one sentence, max 20 words, describing the feel of the riff).

DO NOT invent facts. Only describe what can be inferred from the numbers and notes provided.
Respond with raw JSON only, no markdown fences.

Audio data (measured):
- BPM: {bpm}
- Key: {key}
- Energy level: {energy_word}
- Note density: {density_word}
{f'- Spoken note from guitarist: "{transcript}"' if transcript else ""}
{f'- Manual notes: "{user_notes}"' if user_notes else ""}

Example response:
{{"tags": ["heavy", "riff", "palm-muted"], "description": "A heavy low-register riff with dense note activity."}}"""

        raw = self._chat(prompt)
        # Strip any accidental markdown
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        try:
            data = json.loads(raw)
            tags = [str(t).lower().strip() for t in data.get("tags", [])[:8]]
            description = str(data.get("description", "")).strip()
            return {"tags": tags, "description": description}
        except Exception:
            return {"tags": [], "description": ""}

    def parse_search_intent(self, query: str) -> dict:
        """
        Converts a natural-language query into structured search filters.
        The LLM interprets intent; the database does the retrieval.
        Returns a dict with optional keys: bpm_min, bpm_max, key, tags, text.
        """
        prompt = f"""You are a search assistant for a guitar riff library.
Convert the user's natural-language query into a JSON search filter object.

Allowed keys (all optional):
- "bpm_min": integer (minimum BPM)
- "bpm_max": integer (maximum BPM)
- "key": string (e.g. "C Minor", "Drop D", "E Major")
- "tags": array of strings (style/genre keywords to match)
- "text": string (free-text to search in descriptions/transcripts)

Rules:
- Only include keys that are clearly implied by the query.
- Do NOT invent database records.
- If the query is entirely free-text with no numeric/key hints, return {{"text": "<query>"}} only.
- Respond with raw JSON only, no markdown fences.

Query: "{query}"

Example: "heavy Drop C riffs around 140 bpm"
Response: {{"key": "Drop C", "bpm_min": 130, "bpm_max": 150, "tags": ["heavy"]}}"""

        raw = self._chat(prompt)
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        try:
            return json.loads(raw)
        except Exception:
            # Fallback: treat as free-text search
            return {"text": query}


def get_llm_service() -> LLMService:
    return LocalOllamaService()
