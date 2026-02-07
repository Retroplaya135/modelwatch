"""Fetch, validate, normalize, and export a public model catalog."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.request import Request, urlopen

CATALOG_URL = "https://openrouter.ai/api/v1/models"
USER_AGENT = "Modelwatch/0.1"
MAX_RESPONSE_BYTES = 5_000_000


class CatalogError(RuntimeError):
    """Raised when the upstream catalog cannot be validated."""


def _is_zero(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return False
    try:
        return Decimal(str(value).strip()) == 0
    except (InvalidOperation, ValueError):
        return False


def is_free(model: Mapping[str, Any]) -> bool:
    identifier = str(model.get("id") or "")
    if identifier.endswith(":free"):
        return True
    pricing = model.get("pricing")
    return isinstance(pricing, Mapping) and _is_zero(pricing.get("prompt")) and _is_zero(pricing.get("completion"))


def normalize_model(model: Mapping[str, Any]) -> dict[str, Any]:
    identifier = str(model.get("id") or "")
    architecture = model.get("architecture") if isinstance(model.get("architecture"), Mapping) else {}
    pricing = model.get("pricing") if isinstance(model.get("pricing"), Mapping) else {}
    return {
        "id": identifier,
        "name": model.get("name"),
        "provider": identifier.split("/", 1)[0] if "/" in identifier else "",
        "context_length": model.get("context_length"),
        "description": model.get("description"),
        "pricing": {
            "prompt": pricing.get("prompt"),
            "completion": pricing.get("completion"),
            "image": pricing.get("image"),
            "request": pricing.get("request"),
        },
        "architecture": {
            "modality": architecture.get("modality"),
            "input_modalities": architecture.get("input_modalities"),
            "output_modalities": architecture.get("output_modalities"),
            "tokenizer": architecture.get("tokenizer"),
            "instruct_type": architecture.get("instruct_type"),
        },
        "per_request_limits": model.get("per_request_limits"),
    }


def parse_catalog(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, Mapping):
        raise CatalogError("catalog response must be a JSON object")
    data = payload.get("data")
    if not isinstance(data, list):
        raise CatalogError("catalog response must contain a data array")
    if any(not isinstance(item, Mapping) for item in data):
        raise CatalogError("every catalog entry must be an object")
    return [dict(item) for item in data]


def fetch_catalog(
    *,
    timeout: float = 30.0,
    opener: Callable[..., Any] = urlopen,
    max_response_bytes: int = MAX_RESPONSE_BYTES,
) -> list[dict[str, Any]]:
    request = Request(CATALOG_URL, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with opener(request, timeout=timeout) as response:
            status = int(getattr(response, "status", response.getcode()))
            if status != 200:
                raise CatalogError(f"catalog request returned HTTP {status}")
            content_type = response.headers.get_content_type()
            if content_type != "application/json" and not content_type.endswith("+json"):
                raise CatalogError(f"catalog response was {content_type}, not JSON")
            raw = response.read(max_response_bytes + 1)
    except CatalogError:
        raise
    except OSError as exc:
        raise CatalogError(f"catalog request failed: {exc}") from exc
    if len(raw) > max_response_bytes:
        raise CatalogError(f"catalog response exceeded {max_response_bytes} bytes")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CatalogError("catalog response was not valid UTF-8 JSON") from exc
    return parse_catalog(payload)


def free_models(models: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = [normalize_model(model) for model in models if is_free(model)]
    return sorted(result, key=lambda item: (str(item.get("provider") or ""), str(item.get("name") or ""), str(item.get("id") or "")))


def _markdown_cell(value: Any) -> str:
    return " ".join(str(value or "").split()).replace("|", "\\|")


def render_markdown(models: Sequence[Mapping[str, Any]], generated_at: str) -> str:
    lines = [
        "# Zero-priced model catalog",
        "",
        f"Generated: {generated_at}",
        "",
        "| Provider | Model | Context | Modality |",
        "|---|---|---:|---|",
    ]
    for model in models:
        architecture = model.get("architecture") if isinstance(model.get("architecture"), Mapping) else {}
        lines.append(
            "| {} | {} | {} | {} |".format(
                _markdown_cell(model.get("provider")),
                _markdown_cell(model.get("name")),
                _markdown_cell(model.get("context_length") or "—"),
                _markdown_cell(architecture.get("modality") or "—"),
            )
        )
    return "\n".join(lines) + "\n"


def write_export(
    models: Sequence[Mapping[str, Any]],
    out_dir: Path,
    *,
    now: datetime | None = None,
) -> tuple[Path, Path]:
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise ValueError("now must include timezone information")
    moment = moment.astimezone(timezone.utc)
    generated_at = moment.isoformat().replace("+00:00", "Z")
    stem = f"free-models-{moment.strftime('%Y%m%dT%H%M%SZ')}"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{stem}.json"
    markdown_path = out_dir / f"{stem}.md"
    payload = {"generated_at": generated_at, "source": CATALOG_URL, "count": len(models), "models": list(models)}
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(models, generated_at), encoding="utf-8")
    return json_path, markdown_path
