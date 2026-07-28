from __future__ import annotations

import httpx
import pytest

from portfolio.integrations.nvidia import NvidiaClient, RevisionRequest


def test_validate_key_returns_all_models_and_disables_non_text_models(respx_mock):
    respx_mock.get("https://integrate.api.nvidia.com/v1/models").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {"id": "meta/llama-3.1-70b-instruct", "object": "model"},
                    {"id": "nvidia/nv-embedqa-e5-v5", "object": "model"},
                ]
            },
        )
    )

    models = NvidiaClient().validate_key("nvapi-secret")

    assert [model.id for model in models] == [
        "meta/llama-3.1-70b-instruct",
        "nvidia/nv-embedqa-e5-v5",
    ]
    assert models[0].enabled is True
    assert models[1].enabled is False
    assert "not a chat/text revision model" in models[1].disabled_reason


def test_validate_key_raises_for_invalid_key(respx_mock):
    respx_mock.get("https://integrate.api.nvidia.com/v1/models").mock(
        return_value=httpx.Response(401, json={"error": "unauthorized"})
    )

    with pytest.raises(httpx.HTTPStatusError):
        NvidiaClient().validate_key("bad")


def test_revise_returns_model_suggestion(respx_mock):
    respx_mock.post("https://integrate.api.nvidia.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Revised copy"}}]},
        )
    )

    suggestion = NvidiaClient().revise(
        RevisionRequest(
            api_key="nvapi-secret",
            model="meta/llama-3.1-70b-instruct",
            source_markdown="Original copy",
            action="clarity",
        )
    )

    assert suggestion.suggestion_markdown == "Revised copy"
    assert suggestion.source_hash


def test_revise_redacts_errors(respx_mock):
    respx_mock.post("https://integrate.api.nvidia.com/v1/chat/completions").mock(
        return_value=httpx.Response(500, json={"error": "nvapi-secret leaked"})
    )

    with pytest.raises(RuntimeError) as exc_info:
        NvidiaClient().revise(
            RevisionRequest(
                api_key="nvapi-secret",
                model="meta/llama-3.1-70b-instruct",
                source_markdown="Original copy",
                action="clarity",
            )
        )

    assert "nvapi-secret" not in str(exc_info.value)
