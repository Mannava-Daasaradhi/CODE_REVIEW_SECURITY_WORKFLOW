import sys
import json
import requests
def query_ollama(prompt: str, model: str, stream: bool = False) -> str:
    url = "http://localhost:11434/api/generate"
    try:
        kwargs = {"stream": True, "timeout": (10, None)} if stream else {"timeout": 120}
        resp = requests.post(
            url, 
            json={"model": model, "prompt": prompt, "stream": stream}, 
            **kwargs
        )
    except requests.exceptions.ConnectionError:
        raise ConnectionError("Ollama is not running on localhost:11434")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Ollama request failed: {e}") from e
    if resp.status_code != 200:
        raise RuntimeError(f"Ollama error: {resp.status_code}")
    if not stream:
        return resp.json()["response"]
    full_resp = []
    for line in resp.iter_lines():
        if line:
            chunk = json.loads(line).get("response", "")
            print(chunk, end="", file=sys.stderr, flush=True)
            full_resp.append(chunk)
    return "".join(full_resp)
def list_models() -> list[str]:
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        pass
    return []