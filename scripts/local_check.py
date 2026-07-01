"""Operator command: check whether the configured local model endpoint is reachable.

Run ``make local-check`` (or ``python -m scripts.local_check``). Uses only the free
model-list call (``/v1/models``) — never a generation — so it costs nothing to run and
mirrors ``make gemini-check`` for the DGX Spark provider (STORY_025). Exit code 0 when
the endpoint answers with at least one model, 1 otherwise.
"""

from __future__ import annotations

from app.config import get_settings
from app.services import local_client


def main() -> int:
    settings = get_settings()
    if not settings.local_model_base_url:
        print("Local model: ⚠️  no LOCAL_MODEL_BASE_URL configured — local provider disabled.")
        return 1
    probe = local_client.probe_models(settings.local_model_base_url, settings.local_model_api_key)
    if probe.ok and probe.models:
        print(
            f"Local model: ✅ reachable ({len(probe.models)} models "
            f"at {settings.local_model_base_url})"
        )
        return 0
    print(f"Local model: ❌ {probe.reason or 'no models returned'}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
