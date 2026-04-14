import requests


def get_embedding(text: str, model: str = "nomic-embed-text") -> list[float]:
    try:
        resp = requests.post(
            "http://localhost:11434/api/embeddings",
            json={"model": model, "prompt": text},
            timeout=30,
        )
    except requests.exceptions.ConnectionError:
        raise ConnectionError("Ollama is not running on localhost:11434")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Ollama request failed: {e}") from e

    if resp.status_code == 404:
        raise ValueError(f"Model '{model}' not found. Run: ollama pull {model}")
    if resp.status_code != 200:
        raise RuntimeError(f"Ollama error: {resp.status_code}")

    return resp.json()["embedding"]


def embed_finding(finding: dict) -> str:
    type_or_line = finding.get("type") or (
        f"line {finding['line']}" if finding.get("line") else "unknown"
    )
    description = finding.get("description") or ""
    fix = finding.get("fix") or ""
    return f"{type_or_line} {description} {fix}".strip()