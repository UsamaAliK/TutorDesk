import json
import re

from google import genai
from google.genai import types
from google.genai.errors import APIError

from backend.config import settings


_client = None

_FENCE_PATTERN = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")
_BLANK_RUN_PATTERN = re.compile(r"\n{3,}")

TRANSCRIBE_PROMPT = """
You are a speech-to-text engine. Listen to the audio and decide whether it contains
human speech.

If the audio contains NO human speech at all (silence, background noise, hum, music,
paper rustling, or no audible voice), reply with JSON where "has_speech" is false and
"text" is an empty string.

If the audio DOES contain speech, reply with JSON where "has_speech" is true and "text"
holds the verbatim transcript.

Never invent content. Never guess. Never transcribe imagined words. If you cannot clearly
hear a voice, set "has_speech" to false. A model that invents a question from silence is
far worse than one that reports nothing.

The speaker is dictating a request to an AI teaching assistant. Transcribe the request
exactly as spoken and never answer it. Keep subject-matter terminology as spoken, use
natural punctuation and capitalisation, and prefix a change of speaker with
"Speaker 1:", "Speaker 2:" and so on when more than one person is clearly audible.
""".strip()

RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "has_speech": types.Schema(type=types.Type.BOOLEAN),
        "text": types.Schema(type=types.Type.STRING),
    },
    required=["has_speech", "text"],
)


class TranscribeRateLimited(Exception):
    pass


class TranscribeFailed(Exception):
    pass


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    return _client


def normalize_mime_type(content_type: str) -> str:
    """Map a browser recording MIME type onto one Gemini accepts."""
    if not content_type:
        return ""
    base = content_type.split(";")[0].strip().lower()
    if base.startswith("audio/"):
        return base
    for candidate in settings.SUPPORTED_AUDIO_MIME_TYPES:
        if content_type.strip().lower() == candidate:
            return candidate
    return base


def is_supported_mime_type(mime_type: str) -> bool:
    return mime_type in settings.SUPPORTED_AUDIO_MIME_TYPES


def clean_transcript(text: str) -> str:
    """Strip markdown fences and surrounding quotes from the transcript field."""
    if not text:
        return ""
    value = text.strip()
    value = _FENCE_PATTERN.sub("", value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1].strip()
    return _BLANK_RUN_PATTERN.sub("\n\n", value)


def parse_transcription(raw: str) -> str:
    """Read the structured response and return a transcript, or '' when there is no speech."""
    if not raw:
        return ""
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError) as error:
        raise TranscribeFailed("Could not read the transcription response") from error
    if not isinstance(payload, dict):
        raise TranscribeFailed("Unexpected transcription response shape")
    if not payload.get("has_speech"):
        return ""
    return clean_transcript(payload.get("text") or "")


def transcribe_audio(data: bytes, mime_type: str) -> str:
    """Transcribe recorded audio with Gemini. Returns an empty string when there is no speech."""
    audio_part = types.Part.from_bytes(data=data, mime_type=mime_type)
    try:
        response = _get_client().models.generate_content(
            model=settings.transcribe_model,
            contents=[TRANSCRIBE_PROMPT, audio_part],
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                response_schema=RESPONSE_SCHEMA,
            ),
        )
    except APIError as error:
        if getattr(error, "code", None) == 429 or getattr(error, "status_code", None) == 429:
            raise TranscribeRateLimited("Gemini transcription rate limit reached") from error
        raise TranscribeFailed("Transcription service is unavailable") from error
    return parse_transcription(response.text)
