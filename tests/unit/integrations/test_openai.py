from __future__ import annotations

import httpx
import pytest

from portfolio.integrations.openai import OpenAIClient, RevisionRequest, SeoOptimizationRequest


def test_validate_key_returns_all_models_and_disables_non_text_models(respx_mock):
    respx_mock.get("https://api.openai.com/v1/models").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {"id": "gpt-4o-mini", "object": "model"},
                    {"id": "text-embedding-3-small", "object": "model"},
                ]
            },
        )
    )

    models = OpenAIClient().validate_key("openai-secret")

    assert [model.id for model in models] == ["gpt-4o-mini", "text-embedding-3-small"]
    assert models[0].enabled is True
    assert models[1].enabled is False
    assert "not a chat/text revision model" in models[1].disabled_reason


def test_validate_key_raises_for_invalid_key(respx_mock):
    respx_mock.get("https://api.openai.com/v1/models").mock(
        return_value=httpx.Response(401, json={"error": "unauthorized"})
    )

    with pytest.raises(httpx.HTTPStatusError):
        OpenAIClient().validate_key("bad")


def test_revise_returns_model_suggestion(respx_mock):
    respx_mock.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Revised copy"}}]},
        )
    )

    suggestion = OpenAIClient().revise(
        RevisionRequest(
            api_key="openai-secret",
            model="gpt-4o-mini",
            source_markdown="Original copy",
            action="clarity",
        )
    )

    assert suggestion.suggestion_markdown == "Revised copy"
    assert suggestion.source_hash


def test_revise_redacts_errors(respx_mock):
    respx_mock.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(500, json={"error": "openai-secret leaked"})
    )

    with pytest.raises(RuntimeError) as exc_info:
        OpenAIClient().revise(
            RevisionRequest(
                api_key="openai-secret",
                model="gpt-4o-mini",
                source_markdown="Original copy",
                action="clarity",
            )
        )

    assert "openai-secret" not in str(exc_info.value)


def test_optimize_seo_parses_json_response(respx_mock):
    respx_mock.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": """
                            {
                              "target_queries": [
                                "software workflow portfolio",
                                "database automation"
                              ],
                              "seo_title": "Software Workflow Portfolio | Jeremy Guill",
                              "seo_description": "Practical software and workflow portfolio.",
                              "visible_summary": "Practical software and workflow automation work.",
                              "rationale": "Targets practical implementation searches."
                            }
                            """
                        }
                    }
                ]
            },
        )
    )

    result = OpenAIClient().optimize_seo(
        SeoOptimizationRequest(
            api_key="openai-secret",
            model="gpt-4o-mini",
            entity_type="profile",
            title="Jeremy Guill",
            summary="Summary",
            body="Body",
        )
    )

    assert result.target_queries == ["software workflow portfolio", "database automation"]
    assert result.seo_title == "Software Workflow Portfolio | Jeremy Guill"


def test_optimize_seo_reports_http_status_without_leaking_key(respx_mock):
    respx_mock.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(404, json={"error": "model not found for openai-secret"})
    )

    with pytest.raises(RuntimeError) as exc_info:
        OpenAIClient().optimize_seo(
            SeoOptimizationRequest(
                api_key="openai-secret",
                model="gpt-4o-mini",
                entity_type="profile",
                title="Jeremy Guill",
                summary="Summary",
                body="Body",
            )
        )

    message = str(exc_info.value)
    assert "OpenAI SEO request failed" in message
    assert "404" in message
    assert "gpt-4o-mini" in message
    assert "openai-secret" not in message


def test_optimize_seo_falls_back_to_ollama_when_openai_fails(respx_mock):
    respx_mock.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(429, json={"error": "rate limit"})
    )
    ollama_route = respx_mock.post("http://localhost:11434/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"target_queries": ["ollama fallback"], "seo_title": "T",'
                                ' "seo_description": "D", "visible_summary": "S", "rationale": "R"}'
                            )
                        }
                    }
                ]
            },
        )
    )

    result = OpenAIClient(
        fallback_base_url="http://localhost:11434/v1"
    ).optimize_seo(
        SeoOptimizationRequest(
            api_key="ollama",
            model="gpt-4o-mini",
            entity_type="profile",
            title="Jeremy Guill",
            summary="Summary",
            body="Body",
        )
    )

    assert ollama_route.called
    assert result.seo_title == "T"
