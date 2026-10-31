"""summariser.py - Featherless (OpenAI-compatible) uncertainty-aware wildlife summary."""
import json, os
from config import BASE
from dotenv import load_dotenv

load_dotenv(BASE / ".env")

SYSTEM_PROMPT = """You are a wildlife ecologist analysing camera-trap data.
Write clear, concise summaries for field researchers.
Always mention: how many images are unverified, any species with low confidence,
and whether conclusions are preliminary due to data limitations.
Do not overstate certainty."""


def _client():
    from openai import OpenAI
    key = os.getenv("FEATHERLESS_API_KEY")
    if not key:
        raise RuntimeError("FEATHERLESS_API_KEY is missing from .env")
    return OpenAI(api_key=key.strip(), base_url=os.getenv("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1"))


def build_prompt(stats: dict) -> str:
    return f"""Here are detection statistics from a camera-trap wildlife survey.
Write a 3-paragraph summary covering:
1. Overall wildlife activity and dominant species.
2. Temporal and spatial patterns (time of day, hotspot locations).
3. Data limitations and caveats (unverified images, low-confidence predictions).

Survey data:
{json.dumps(stats, indent=2, default=str)}"""


def _messages(stats):
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": build_prompt(stats)}]


MODEL = "mistralai/Mistral-7B-Instruct-v0.2"


def summarise_text(stats: dict, model: str = MODEL) -> str:
    r = _client().chat.completions.create(model=model, messages=_messages(stats), temperature=0.4, max_tokens=700)
    return r.choices[0].message.content


def summarise(stats: dict, model: str = MODEL, stream: bool = True):
    """Generator of text chunks (for st.write_stream)."""
    resp = _client().chat.completions.create(model=model, messages=_messages(stats),
                                             stream=True, temperature=0.4, max_tokens=700)
    for chunk in resp:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
