"""Operator command: check whether the configured GEMINI_API_KEY is valid.

Run ``make gemini-check`` (or ``python -m scripts.gemini_check``). Uses only the
free model-list call — never a paid ``generateContent`` — so it costs nothing to
run, and it reports the same status the Shoots / New-job pickers surface (STORY_023).
Exit code 0 when the key works, 1 otherwise (handy for scripts / health checks).
"""

from __future__ import annotations

from app.services import generation_service


def main() -> int:
    status = generation_service.gemini_status()
    if status.ok:
        print(f"Gemini key: ✅ valid ({len(status.models)} models available)")
        return 0
    print(f"Gemini key: ❌ {status.detail}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
