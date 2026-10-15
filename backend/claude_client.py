"""The ONE shared helper that every experiment uses to call Claude.

Why one helper? Every experiment needs the same things back (text, token
counts, stop reason, cost). Doing it in one place keeps the numbers you see on
every page consistent, and keeps the "is this setting supported?" checks in
one spot instead of scattered across pages.
"""
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterator, List, Optional

import anthropic

from backend import spend
from backend.config import load_config, model_info

# The SDK reads ANTHROPIC_API_KEY from the environment (loaded from .env by
# backend.config). Creating the client once and reusing it is cheaper than
# creating one per request, because it reuses network connections.
# max_retries=4: experiments that repeat a call many times can hit the
# per-minute rate limit; the SDK then waits and retries automatically.
_client = anthropic.Anthropic(max_retries=4)


class UnsupportedFeatureError(ValueError):
    """Raised BEFORE calling the API when a setting won't work on the model.

    Checking first saves you a wasted API call and gives a clearer message
    than the raw API error would.
    """


@dataclass
class ClaudeResult:
    text: str
    input_tokens: int
    output_tokens: int
    stop_reason: Optional[str]
    estimated_cost_usd: float
    model: str
    latency_s: float  # wall-clock seconds for the API call

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Turn token counts into dollars using the prices in config.yaml.

    Why compute it ourselves? The API reports tokens, not money. Prices are
    per MILLION tokens, so we divide by 1,000,000.
    """
    info = model_info(model)
    in_price = info["input_price_per_mtok"]
    out_price = info["output_price_per_mtok"]

    # Some models charge more when the prompt is very long.
    threshold = info.get("long_prompt_threshold_tokens")
    if threshold and input_tokens > threshold:
        in_price = info.get("long_prompt_input_price_per_mtok", in_price)
        out_price = info.get("long_prompt_output_price_per_mtok", out_price)

    return (input_tokens * in_price + output_tokens * out_price) / 1_000_000


def _check_supported(
    model: str,
    messages: List[Dict[str, Any]],
    temperature: Optional[float],
    top_p: Optional[float],
    top_k: Optional[int],
) -> None:
    """Refuse settings the model is known to reject, with a clear explanation."""
    info = model_info(model)
    sampling_model = load_config().get("sampling_model")

    uses_sampling = any(v is not None for v in (temperature, top_p, top_k))
    if uses_sampling and not info.get("supports_sampling_params", False):
        raise UnsupportedFeatureError(
            f"{model} does not accept temperature / top_p / top_k. "
            f"Use the sampling model ('{sampling_model}') for this experiment."
        )

    if (
        temperature is not None
        and top_p is not None
        and not info.get("allows_temperature_and_top_p_together", True)
    ):
        raise UnsupportedFeatureError(
            f"{model} does not allow temperature and top_p in the same request. "
            f"Pick one of them."
        )

    # "Prefill" = the last message is from the assistant, so Claude continues
    # that text instead of starting a fresh reply.
    if messages and messages[-1].get("role") == "assistant":
        if not info.get("supports_prefill", False):
            raise UnsupportedFeatureError(
                f"{model} does not support continuing an assistant message "
                f"(prefill). Use the sampling model ('{sampling_model}')."
            )


def call_claude(
    messages: List[Dict[str, Any]],
    *,
    model: Optional[str] = None,
    system: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    top_k: Optional[int] = None,
) -> ClaudeResult:
    """Send one request to Claude and return a ClaudeResult.

    `messages` uses the Anthropic format:
        [{"role": "user", "content": "Hello"}, ...]
    Settings left as None are simply not sent, so the API uses its default.
    """
    model = model or load_config()["default_model"]
    kwargs = _build_request(model, messages, system, max_tokens, temperature, top_p, top_k)

    spend.check_budget()  # refuse BEFORE spending anything
    start = time.perf_counter()
    response = _client.messages.create(**kwargs)

    # A response is a list of content blocks (text, thinking, ...). We only
    # want the visible text, so we join the text blocks.
    text = "".join(block.text for block in response.content if block.type == "text")

    result = ClaudeResult(
        text=text,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        stop_reason=response.stop_reason,
        estimated_cost_usd=estimate_cost(
            model, response.usage.input_tokens, response.usage.output_tokens
        ),
        model=model,
        latency_s=round(time.perf_counter() - start, 3),
    )
    spend.record(result.estimated_cost_usd)
    return result


def _build_request(
    model: str,
    messages: List[Dict[str, Any]],
    system: Optional[str],
    max_tokens: int,
    temperature: Optional[float],
    top_p: Optional[float],
    top_k: Optional[int],
) -> Dict[str, Any]:
    """Validate the settings and turn them into keyword arguments for the SDK.

    Shared by call_claude and stream_claude so both follow the same rules.
    """
    _check_supported(model, messages, temperature, top_p, top_k)

    # The API rejects a prefill (final assistant message) that ends with
    # whitespace. Trimming it is safe: the model's next token usually starts
    # with its own leading space (e.g. " Paris"), so nothing is lost.
    if messages and messages[-1].get("role") == "assistant":
        messages = messages[:-1] + [
            {**messages[-1], "content": messages[-1]["content"].rstrip()}
        ]

    # Only include optional settings that were actually chosen. Sending
    # temperature=None would be an error; leaving it out means "default".
    kwargs: Dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system
    if temperature is not None:
        kwargs["temperature"] = temperature
    if top_p is not None:
        kwargs["top_p"] = top_p
    if top_k is not None:
        kwargs["top_k"] = top_k

    # Haiku 5.5 "thinks" before answering by default. For these experiments we
    # turn that off: otherwise hidden thinking tokens would use up a tiny
    # max_tokens budget (like max_tokens=1) and muddy the token counts.
    if model_info(model).get("thinking_on_by_default"):
        kwargs["thinking"] = {"type": "disabled"}
    return kwargs


def stream_claude(
    messages: List[Dict[str, Any]],
    *,
    model: Optional[str] = None,
    system: Optional[str] = None,
    max_tokens: int = 1024,
) -> Iterator[Dict[str, Any]]:
    """Like call_claude, but yields the reply piece by piece as it is generated.

    Yields {"type": "text", "text": ..., "t": seconds_since_start} for each
    chunk, then one final {"type": "done", ...} with the same fields as
    ClaudeResult. Recording the time of each chunk lets the UI show that the
    answer really is produced front-to-back, not all at once.
    """
    model = model or load_config()["default_model"]
    kwargs = _build_request(model, messages, system, max_tokens, None, None, None)

    spend.check_budget()
    start = time.perf_counter()
    with _client.messages.stream(**kwargs) as stream:
        for text in stream.text_stream:
            yield {"type": "text", "text": text, "t": round(time.perf_counter() - start, 3)}
        final = stream.get_final_message()

    text = "".join(b.text for b in final.content if b.type == "text")
    cost = estimate_cost(model, final.usage.input_tokens, final.usage.output_tokens)
    spend.record(cost)
    yield {
        "type": "done",
        **ClaudeResult(
            text=text,
            input_tokens=final.usage.input_tokens,
            output_tokens=final.usage.output_tokens,
            stop_reason=final.stop_reason,
            estimated_cost_usd=cost,
            model=model,
            latency_s=round(time.perf_counter() - start, 3),
        ).to_dict(),
    }


def count_tokens(
    messages: List[Dict[str, Any]],
    *,
    model: Optional[str] = None,
    system: Optional[str] = None,
) -> int:
    """Count input tokens WITHOUT generating anything.

    Anthropic's token counting endpoint is free (only rate-limited), so this
    is not checked against or added to the monthly budget. The count is an
    estimate and includes a few tokens of message formatting.
    """
    model = model or load_config()["default_model"]
    kwargs: Dict[str, Any] = {"model": model, "messages": messages}
    if system:
        kwargs["system"] = system
    return _client.messages.count_tokens(**kwargs).input_tokens
