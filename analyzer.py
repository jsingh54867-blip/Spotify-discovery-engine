"""
analyzer.py
Groq-powered analysis engine.
Processes raw reviews in batches → extracts themes, segments, pain points, unmet needs.
"""

import json
import re
import pandas as pd
from groq import Groq


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _chunk(lst: list, size: int):
    """Split a list into chunks of given size."""
    for i in range(0, len(lst), size):
        yield lst[i: i + size]


def _safe_json(text: str) -> dict | list | None:
    """Extract and parse JSON from Groq response, even if wrapped in markdown."""
    text = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        # Try extracting first JSON object/array
        match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                return None
    return None


# ─── Core analysis functions ──────────────────────────────────────────────────

def extract_themes(client: Groq, reviews: list[str]) -> dict:
    """
    Send batches of reviews to Groq.
    Returns aggregated themes with mention counts and representative quotes.
    """
    all_themes = {}

    for batch in _chunk(reviews, 30):  # 30 reviews per call stays within token limits
        batch_text = "\n---\n".join(batch)

        prompt = f"""You are analyzing Spotify user reviews to find music discovery insights.

Below are {len(batch)} user reviews. Extract recurring themes related to music discovery, recommendations, and listening behavior.

For each theme found, return JSON in this exact format:
{{
  "themes": [
    {{
      "name": "short theme name",
      "description": "one sentence explaining this theme",
      "mention_count": number,
      "sentiment": "negative" | "positive" | "neutral",
      "representative_quote": "exact short quote from the reviews"
    }}
  ]
}}

Focus only on themes about:
- Music discovery problems
- Recommendation frustrations  
- Repetitive listening behavior
- Unmet listening needs
- User segment differences

Reviews:
{batch_text}

Return ONLY the JSON. No explanation."""

        try:
            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
            )
            result = _safe_json(response.choices[0].message.content)
            if result and "themes" in result:
                for theme in result["themes"]:
                    name = theme["name"].lower().strip()
                    if name in all_themes:
                        all_themes[name]["mention_count"] += theme.get("mention_count", 1)
                    else:
                        all_themes[name] = theme
        except Exception:
            continue

    return all_themes


def segment_users(client: Groq, reviews: list[str]) -> list[dict]:
    """
    Identify distinct user segments from the reviews.
    Each segment has different discovery challenges.
    """
    sample = reviews[:60]  # use a representative sample
    batch_text = "\n---\n".join(sample)

    prompt = f"""You are a product researcher analyzing Spotify user reviews.

Identify 4-5 distinct USER SEGMENTS based on their listening behavior and discovery challenges.

Return JSON in this exact format:
{{
  "segments": [
    {{
      "name": "segment name",
      "description": "who they are in one sentence",
      "size_estimate": "small | medium | large",
      "discovery_challenge": "their specific discovery problem",
      "listening_behavior": "how they typically listen",
      "unmet_need": "what they actually want but don't have",
      "example_quote": "a short representative quote from the reviews"
    }}
  ]
}}

Reviews to analyze:
{batch_text}

Return ONLY the JSON. No explanation."""

    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000,
        )
        result = _safe_json(response.choices[0].message.content)
        if result and "segments" in result:
            return result["segments"]
    except Exception:
        pass

    return []


def extract_unmet_needs(client: Groq, reviews: list[str]) -> list[dict]:
    """
    Find the top unmet needs that consistently appear across all sources.
    """
    sample = reviews[:80]
    batch_text = "\n---\n".join(sample)

    prompt = f"""You are analyzing Spotify reviews to find unmet user needs around music discovery.

From these reviews, identify the 6 most important UNMET NEEDS — things users clearly want but Spotify doesn't currently provide well.

Return JSON in this exact format:
{{
  "unmet_needs": [
    {{
      "need": "short name of the need",
      "explanation": "what users actually want",
      "frequency": "how often this appears: very common | common | occasional",
      "current_gap": "what Spotify does now that falls short",
      "opportunity": "what solving this could unlock",
      "supporting_quote": "short quote from reviews"
    }}
  ]
}}

Reviews:
{batch_text}

Return ONLY the JSON. No explanation."""

    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000,
        )
        result = _safe_json(response.choices[0].message.content)
        if result and "unmet_needs" in result:
            return result["unmet_needs"]
    except Exception:
        pass

    return []


def answer_question(client: Groq, question: str, reviews: list[str], themes: dict) -> str:
    """
    Answer a specific research question using the collected reviews + themes.
    This powers the Q&A interface in the Streamlit app.
    """
    sample = reviews[:50]
    reviews_text = "\n---\n".join(sample)
    themes_text = json.dumps(list(themes.values())[:10], indent=2) if themes else "Not yet analyzed"

    prompt = f"""You are a senior product researcher who has analyzed thousands of Spotify user reviews.

Answer this research question concisely but with depth:
"{question}"

Use the evidence below. Be specific. Cite user behavior patterns. Reference actual user language where relevant.
Structure your answer in 3-4 short paragraphs. Do not use bullet points. Write like a researcher briefing a PM.

IDENTIFIED THEMES:
{themes_text}

SAMPLE REVIEWS:
{reviews_text}

Answer the question directly. Be honest about limitations in the data."""

    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not generate answer: {e}"


# ─── Master analyzer ──────────────────────────────────────────────────────────

def run_full_analysis(api_key: str, df: pd.DataFrame) -> dict:
    """
    Runs the complete analysis pipeline on a collected DataFrame.
    Returns a results dict with themes, segments, and unmet needs.
    """
    client = Groq(api_key=api_key)
    reviews = df["text"].tolist()

    results = {
        "total_reviews": len(reviews),
        "source_breakdown": df["source"].value_counts().to_dict(),
        "themes": {},
        "segments": [],
        "unmet_needs": [],
        "client": client,
        "reviews": reviews,
    }

    results["themes"] = extract_themes(client, reviews)
    results["segments"] = segment_users(client, reviews)
    results["unmet_needs"] = extract_unmet_needs(client, reviews)

    return results
