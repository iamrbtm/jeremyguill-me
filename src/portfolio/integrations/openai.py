from __future__ import annotations

import hashlib
import json
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
class OpenAIModel:
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


@dataclass(frozen=True)
class SeoOptimizationRequest:
    api_key: str
    model: str
    entity_type: str
    title: str
    summary: str
    body: str
    current_target_query: str = ""


@dataclass(frozen=True)
class SeoOptimizationResult:
    target_queries: list[str]
    seo_title: str
    seo_description: str
    visible_summary: str
    rationale: str


class OpenAIClient:
    DEFAULT_BASE_URL = "https://api.openai.com/v1"

    def __init__(
        self,
        http: httpx.Client | None = None,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        fallback_base_url: str | None = None,
    ) -> None:
        import os

        self.base_url = (
            base_url or os.getenv("OPENAI_BASE_URL") or self.DEFAULT_BASE_URL
        ).rstrip("/")
        self.default_api_key = api_key or os.getenv("OPENAI_API_KEY") or "ollama"
        self.fallback_base_url = (
            fallback_base_url or os.getenv("OPENAI_FALLBACK_BASE_URL")
        )
        self.fallback_model = os.getenv("OPENAI_FALLBACK_MODEL")
        self.http = http or httpx.Client()

    def _fallback_client(self) -> "OpenAIClient":
        return OpenAIClient(
            base_url=self.fallback_base_url,
            api_key=self.default_api_key,
            fallback_base_url=None,
            http=self.http,
        )

    def _should_fallback(self, exc: httpx.HTTPError) -> bool:
        if not self.fallback_base_url:
            return False
        response = getattr(exc, "response", None)
        if response is None:
            return True
        return response.status_code in {401, 403, 429} or response.status_code >= 500

    def validate_key(self, api_key: str) -> list[OpenAIModel]:
        response = self.http.get(
            f"{self.base_url}/models",
            headers={"Authorization": f"Bearer {api_key or self.default_api_key}"},
            timeout=10.0,
        )
        response.raise_for_status()
        return [classify_model(item) for item in response.json().get("data", [])]

    def revise(self, request: RevisionRequest) -> RevisionSuggestion:
        if request.action not in TEXT_REVISION_ACTIONS:
            raise ValueError("Unsupported revision action")
        try:
            response = self.http.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {request.api_key or self.default_api_key}"},
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
            if self._should_fallback(exc):
                fallback = self._fallback_client()
                fallback_request = RevisionRequest(
                    api_key=self.default_api_key,
                    model=self.fallback_model or request.model,
                    source_markdown=request.source_markdown,
                    action=request.action,
                    custom_prompt=request.custom_prompt,
                )
                return fallback.revise(fallback_request)
            raise RuntimeError(
                _http_error_message("OpenAI revision request failed", exc, request.model)
            ) from exc
        payload = response.json()
        suggestion = payload["choices"][0]["message"]["content"].strip()
        return RevisionSuggestion(
            suggestion_markdown=suggestion,
            source_hash=hash_source(request.source_markdown),
            model=request.model,
            action=request.action,
        )

    def optimize_seo(self, request: SeoOptimizationRequest) -> SeoOptimizationResult:
        try:
            response = self.http.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {request.api_key or self.default_api_key}"},
                json={
                    "model": request.model,
                    "messages": [
                        {"role": "system", "content": _seo_system_prompt()},
                        {"role": "user", "content": _seo_user_prompt(request)},
                    ],
                    "temperature": 0.3,
                },
                timeout=30.0,
            )
            response.raise_for_status()
        except httpx.TimeoutException:
            raise
        except httpx.HTTPError as exc:
            if self._should_fallback(exc):
                fallback = self._fallback_client()
                fallback_request = SeoOptimizationRequest(
                    api_key=self.default_api_key,
                    model=self.fallback_model or request.model,
                    entity_type=request.entity_type,
                    title=request.title,
                    summary=request.summary,
                    body=request.body,
                    current_target_query=request.current_target_query,
                )
                return fallback.optimize_seo(fallback_request)
            raise RuntimeError(
                _http_error_message("OpenAI SEO request failed", exc, request.model)
            ) from exc
        content = response.json()["choices"][0]["message"]["content"].strip()
        payload = _loads_json_object(content)
        return SeoOptimizationResult(
            target_queries=_clean_string_list(
                payload.get("target_queries"), limit=5, max_length=180
            ),
            seo_title=_clean_string(payload.get("seo_title"), max_length=180),
            seo_description=_clean_string(payload.get("seo_description"), max_length=320),
            visible_summary=_clean_string(payload.get("visible_summary"), max_length=320),
            rationale=_clean_string(payload.get("rationale"), max_length=500),
        )


def classify_model(item: dict[str, object]) -> OpenAIModel:
    model_id = str(item.get("id", ""))
    disabled_markers = (
        "audio",
        "dall-e",
        "embedding",
        "image",
        "moderation",
        "realtime",
        "search",
        "transcribe",
        "tts",
        "whisper",
    )
    if any(marker in model_id.lower() for marker in disabled_markers):
        return OpenAIModel(model_id, False, "Model is not a chat/text revision model")
    return OpenAIModel(model_id, True)


def hash_source(source_markdown: str) -> str:
    return hashlib.sha256(source_markdown.encode("utf-8")).hexdigest()


def _system_prompt(action: str) -> str:
    return (
        "Revise the supplied Markdown for the requested editorial action. "
        "Return only Markdown. Do not invent facts or metrics. Action: "
        f"{action}."
    )


def _seo_system_prompt() -> str:
    return (
        "You are the autonomous SEO editor for jeremyguill.me. Generate search targets and "
        "metadata for a professional software/workflow portfolio. Preserve facts, meaning, and "
        "tone. Do not invent employers, credentials, metrics, technologies, locations, or claims. "
        "Return only valid JSON with keys: target_queries, seo_title, seo_description, "
        "visible_summary, rationale. target_queries must be an array of concise search phrases."
    )


def _seo_user_prompt(request: SeoOptimizationRequest) -> str:
    return json.dumps(
        {
            "entity_type": request.entity_type,
            "title": request.title,
            "summary": request.summary,
            "body": request.body[:6000],
            "current_target_query": request.current_target_query,
        },
        ensure_ascii=True,
    )


def _loads_json_object(content: str) -> dict[str, object]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").removeprefix("json").strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("OpenAI SEO response did not contain JSON") from exc
        payload = json.loads(cleaned[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("OpenAI SEO response was not a JSON object")
    return payload


def _http_error_message(prefix: str, exc: httpx.HTTPError, model: str) -> str:
    response = getattr(exc, "response", None)
    if response is None:
        return f"{prefix} for model {model}: {exc.__class__.__name__}"
    return f"{prefix} for model {model}: HTTP {response.status_code}"


def _clean_string(value: object, *, max_length: int) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:max_length]


def _clean_string_list(value: object, *, limit: int, max_length: int) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    seen: set[str] = set()
    for item in value:
        cleaned = _clean_string(item, max_length=max_length).lower()
        if cleaned and cleaned not in seen:
            items.append(cleaned)
            seen.add(cleaned)
        if len(items) >= limit:
            break
    return items
