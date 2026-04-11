import requests

def query_ollama(prompt: str, model: str) -> str:
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(url, json=payload, timeout=120)
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError("Ollama not running. Start it with: ollama serve") from e

    if response.status_code == 404:
        raise ValueError(f"Model '{model}' not found. Run: ollama pull {model}")

    response.raise_for_status()

    return response.json()["response"]