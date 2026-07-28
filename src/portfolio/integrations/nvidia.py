from __future__ import annotations

import hashlib
from dataclasses import dataclass

import httpx

TEXT_REVISION_ACTIONS = {
    "grammar",
    "professional",
    "clarity",
    "shorten",
    "expand",
    "format",
    "voice",
    "audience",
    "seo",
    "custom",
}


@dataclass(frozen=True)
class NvidiaModel:
    id: str
    enabled: bool
    disabled_reason: str = ""


@dataclass(frozen=True)
class RevisionRequest:
    api_key: str
    model: str
    source_markdown: str
    action: str
    custom_prompt: str = ""


@dataclass(frozen=True)
class RevisionSuggestion:
    suggestion_markdown: str
    source_hash: str
    model: str
    action: str


class NvidiaClient:
    BASE_URL = "https://integrate.api.nvidia.com/v1"

    def __init__(self, http: httpx.Client | None = None) -> None:
        self.http = http or httpx.Client()

    def validate_key(self, api_key: str) -> list[NvidiaModel]:
        response = self.http.get(
            f"{self.BASE_URL}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        response.raise_for_status()
        return [classify_model(item) for item in response.json().get("data", [])]

    def revise(self, request: RevisionRequest) -> RevisionSuggestion:
        if request.action not in TEXT_REVISION_ACTIONS:
            raise ValueError("Unsupported revision action")
        try:
            response = self.http.post(
                f"{self.BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {request.api_key}"},
                json={
                    "model": request.model,
                    "messages": [
                        {"role": "system", "content": _system_prompt(request.action)},
                        {
                            "role": "user",
                            "content": request.custom_prompt or request.source_markdown,
                        },
                    ],
                    "temperature": 0.2,
                },
                timeout=20.0,
            )
            response.raise_for_status()
        except httpx.TimeoutException:
            raise
        except httpx.HTTPError as exc:
            raise RuntimeError("NVIDIA request failed") from exc
        payload = response.json()
        suggestion = payload["choices"][0]["message"]["content"].strip()
        return RevisionSuggestion(
            suggestion_markdown=suggestion,
            source_hash=hash_source(request.source_markdown),
            model=request.model,
            action=request.action,
        )


def classify_model(item: dict[str, object]) -> NvidiaModel:
    model_id = str(item.get("id", ""))
    disabled_markers = ("embed", "rerank", "vision", "image", "audio", "speech")
    if any(marker in model_id.lower() for marker in disabled_markers):
        return NvidiaModel(model_id, False, "Model is not a chat/text revision model")
    return NvidiaModel(model_id, True)


def hash_source(source_markdown: str) -> str:
    return hashlib.sha256(source_markdown.encode("utf-8")).hexdigest()


def _system_prompt(action: str) -> str:
    return (
        "Revise the supplied Markdown for the requested editorial action. "
        "Return only Markdown. Do not invent facts or metrics. Action: "
        f"{action}."
    )
