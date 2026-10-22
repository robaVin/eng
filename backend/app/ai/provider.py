"""Provider-independent AI adapter — OpenAI implementation.

Only this module knows about the concrete AI SDK (the official `openai` Python SDK).
It exposes two operations — `transcribe` and `evaluate` — that return validated
Pydantic objects. The prompts live in `prompts.py` and are provider-agnostic.

The API key is read from settings/env and never logged or returned.
"""
from __future__ import annotations

import base64
import json
import re

from ..config import settings
from ..schemas import EvaluationResult, TranscriptionResult
from . import prompts

# Vision-capable fallbacks, tried in order when the configured model is unavailable.
FALLBACK_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini"]

_resolved_model: str | None = None


class AIError(RuntimeError):
    """Raised for any AI failure. The message is safe to show the teacher."""


class AINotConfiguredError(AIError):
    pass


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_json_object(text: str) -> dict:
    """Tolerantly extract a JSON object from the model's text output."""
    text = (text or "").strip()
    if not text:
        raise AIError("The AI returned an empty response.")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fenced = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(fenced)
    except json.JSONDecodeError:
        pass
    match = _JSON_RE.search(text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise AIError("The AI returned text that could not be parsed as valid JSON.") from exc
    raise AIError("The AI returned a response that was not in the expected JSON format.")


def _client():
    try:
        import openai
    except ImportError as exc:  # pragma: no cover
        raise AIError("The 'openai' package is not installed.") from exc
    if not settings.ai_configured:
        raise AINotConfiguredError(
            "No AI API key is configured. Set OPENAI_API_KEY in the backend .env file."
        )
    import os

    key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY")
    return openai, openai.OpenAI(api_key=key, timeout=120, max_retries=2)


def resolve_model(openai=None, client=None) -> str:
    """Return a usable vision-capable model id, falling back if the configured one is
    not accessible to this account. Result is cached for the process."""
    global _resolved_model
    if _resolved_model:
        return _resolved_model
    if openai is None or client is None:
        openai, client = _client()

    candidates: list[str] = []
    for m in [settings.ai_model, *FALLBACK_MODELS]:
        if m and m not in candidates:
            candidates.append(m)

    last_err: Exception | None = None
    for model in candidates:
        try:
            client.models.retrieve(model)
            _resolved_model = model
            if model != settings.ai_model:
                print(f"[ai] configured model '{settings.ai_model}' unavailable; using '{model}'")
            return model
        except openai.NotFoundError as exc:
            last_err = exc
            continue
        except openai.AuthenticationError as exc:
            raise AINotConfiguredError("The OpenAI API key was rejected (authentication failed).") from exc
        except openai.APIError as exc:
            last_err = exc
            continue
    raise AIError(
        "No accessible vision-capable OpenAI model was found for this account "
        f"(tried: {', '.join(candidates)})."
    ) from last_err


def current_model() -> str | None:
    """The resolved model, if analysis has run; otherwise None (no API call made)."""
    return _resolved_model


def _chat(openai, client, *, system: str, content: list) -> tuple[str, dict]:
    model = resolve_model(openai, client)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            response_format={"type": "json_object"},
        )
    except openai.AuthenticationError as exc:
        raise AINotConfiguredError("The OpenAI API key was rejected (authentication failed).") from exc
    except openai.RateLimitError as exc:
        raise AIError("The AI service is rate-limited right now. Please try again shortly.") from exc
    except openai.APITimeoutError as exc:
        raise AIError("The AI request timed out. Please try again.") from exc
    except openai.APIConnectionError as exc:
        raise AIError("Could not reach the AI service. Check the network connection.") from exc
    except openai.BadRequestError as exc:
        raise AIError(f"The AI request was rejected: {getattr(exc, 'message', str(exc))}") from exc
    except openai.APIError as exc:
        raise AIError(f"The AI service returned an error: {getattr(exc, 'message', str(exc))}") from exc

    choice = resp.choices[0]
    if choice.finish_reason == "content_filter":
        raise AIError("The AI declined to process this content (content filter).")
    text = choice.message.content or ""
    usage = {
        "input_tokens": getattr(resp.usage, "prompt_tokens", None) if resp.usage else None,
        "output_tokens": getattr(resp.usage, "completion_tokens", None) if resp.usage else None,
        "model": resp.model,
    }
    return text, usage


def _image_block(data: bytes, media_type: str) -> dict:
    b64 = base64.standard_b64encode(data).decode("utf-8")
    return {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}}


def transcribe(
    images: list[tuple[bytes, str]],
    *,
    test_title: str,
    instructions: str,
) -> tuple[TranscriptionResult, dict]:
    """images: ordered list of (bytes, media_type). Returns (result, usage)."""
    if not images:
        raise AIError("No images were provided for transcription.")
    openai, client = _client()
    content: list = [{"type": "text", "text": prompts.transcription_user_text(test_title, instructions)}]
    content += [_image_block(d, m) for d, m in images]
    text, usage = _chat(openai, client, system=prompts.TRANSCRIPTION_SYSTEM, content=content)
    data = _parse_json_object(text)
    try:
        result = TranscriptionResult.model_validate(data)
    except Exception as exc:  # noqa: BLE001  pydantic ValidationError
        raise AIError("The AI transcription response did not match the expected format.") from exc
    if not result.transcription.strip():
        raise AIError("The AI could not extract any student handwriting from the images.")
    return result, usage


def evaluate(
    *,
    test_type: str,
    title: str,
    instructions: str,
    criteria: str,
    max_points: float,
    expected_answer: str | None,
    rubric: list[dict] | None,
    word_min: int | None,
    word_max: int | None,
    transcription: str,
    word_count: int,
) -> tuple[EvaluationResult, dict]:
    openai, client = _client()
    user_text = prompts.evaluation_user_text(
        test_type=test_type,
        title=title,
        instructions=instructions,
        criteria=criteria,
        max_points=max_points,
        expected_answer=expected_answer,
        rubric=rubric,
        word_min=word_min,
        word_max=word_max,
        transcription=transcription,
        word_count=word_count,
    )
    text, usage = _chat(
        openai, client,
        system=prompts.EVALUATION_SYSTEM,
        content=[{"type": "text", "text": user_text}],
    )
    data = _parse_json_object(text)
    try:
        result = EvaluationResult.model_validate(data)
    except Exception as exc:  # noqa: BLE001
        raise AIError("The AI evaluation response did not match the expected format.") from exc
    return result, usage
