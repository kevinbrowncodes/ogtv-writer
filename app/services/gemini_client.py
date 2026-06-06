"""Thin wrapper around the Google Gemini (``google-genai``) SDK.

The ONLY place that talks to the Gemini API. Kept tiny so tests mock ``generate``
at this boundary and never make a live, paid call. The SDK is imported lazily, so
importing the app at rest does not require the package to be installed.
"""

from __future__ import annotations

# Models whose name contains any of these aren't general text generators
# (image / audio / tts / robotics / research / …) — hidden from the script picker.
_NON_TEXT_MARKERS = (
    "image",
    "tts",
    "audio",
    "embedding",
    "aqa",
    "robotics",
    "computer-use",
    "deep-research",
    "lyria",
    "gemma",
    "nano-banana",
    "-er-",
    "customtools",
    "antigravity",
)


def list_models(api_key: str) -> list[str]:
    """Return the Gemini text-generation models this key can use (best-effort).

    Keeps models that support ``generateContent`` and drops non-text modalities
    (see ``_NON_TEXT_MARKERS``). Returns ``[]`` on any error so callers can fall
    back gracefully. The SDK is imported lazily, same as ``generate``.
    """
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        names: list[str] = []
        for model in client.models.list():
            actions = getattr(model, "supported_actions", None) or []
            if "generateContent" not in actions:
                continue
            name = (model.name or "").split("/")[-1]
            if name and not any(marker in name for marker in _NON_TEXT_MARKERS):
                names.append(name)
        return sorted(names)
    except Exception:
        return []


def generate(*, prompt: str, image_bytes: bytes, image_mime: str, model: str, api_key: str) -> str:
    """Send a prompt + image to Gemini and return the response text.

    Raises if the SDK is missing or the call fails; the caller turns that into a
    failed job.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=image_mime),
            prompt,
        ],
    )
    return response.text or ""
