"""Thin wrapper around the Google Gemini (``google-genai``) SDK.

The ONLY place that talks to the Gemini API. Kept tiny so tests mock ``generate``
at this boundary and never make a live, paid call. The SDK is imported lazily, so
importing the app at rest does not require the package to be installed.
"""

from __future__ import annotations


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
