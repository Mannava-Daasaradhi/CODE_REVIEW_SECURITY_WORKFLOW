"""
Baseline inference script.

Runs an OpenAI agent against all three task difficulties and records scores.
Requires the environment server to be running (local or HuggingFace Spaces).

Usage:
    export OPENAI_API_KEY=sk-...
    python baseline/run_baseline.py --env-url http://localhost:7860
    python baseline/run_baseline.py --env-url https://your-space.hf.space

Output: baseline/results.json
"""

import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from openai import OpenAI


DIFFICULTIES = ["easy", "medium", "hard"]
RESULTS_PATH = Path(__file__).parent / "results.json"

SYSTEM_PROMPT = """You are a senior software engineer performing code review and security auditing.

Analyze the provided code carefully and respond ONLY with a valid JSON object in this exact format:
{
  "flagged_lines": [<list of integer line numbers where bugs exist, 1-indexed>],
  "findings": [
    { "type": "<vulnerability type, e.g. sql_injection, hardcoded_secret, xss>", "description": "<explanation>" }
  ],
  "review_text": "<structured code review: include severity labels (critical/high/medium/low), line references (line N or LN), actionable recommendations (should/must/recommend), and category labels (bug/security/vulnerability/style/performance)>"
}

Respond with JSON only. No markdown, no explanation, no code fences."""


def build_user_prompt(observation: dict) -> str:
    return (
        f"Task: {observation['instructions']}\n\n"
        f"Code:\n{observation['code_snippet']}"
    )


def call_agent(client: OpenAI, observation: dict) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(observation)},
        ],
        temperature=0,  # Deterministic output
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    return json.loads(raw)


def run_baseline(env_url: str) -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key)
    results = []

    with httpx.Client(base_url=env_url, timeout=30.0) as http:
        # Health check
        health = http.get("/")
        if health.status_code != 200:
            print(f"ERROR: Environment at {env_url} is not responding.", file=sys.stderr)
            sys.exit(1)
        print(f"Environment healthy: {env_url}\n")

        for difficulty in DIFFICULTIES:
            print(f"Running difficulty: {difficulty}")

            # Reset
            reset_resp = http.post("/reset", json={"task_difficulty": difficulty})
            reset_resp.raise_for_status()
            observation = reset_resp.json()
            print(f"  Episode: {observation['task_id']}")

            # Agent inference
            try:
                action = call_agent(client, observation)
            except Exception as e:
                print(f"  ERROR: Agent call failed: {e}", file=sys.stderr)
                action = {"flagged_lines": [], "findings": [], "review_text": ""}

            # Step
            step_resp = http.post("/step", json=action)
            step_resp.raise_for_status()
            result = step_resp.json()

            reward = result["reward"]
            info = result.get("info", {})
            print(f"  Reward: {reward:.4f}  Info: {info}\n")

            results.append({
                "difficulty": difficulty,
                "task_id": observation["task_id"],
                "reward": reward,
                "info": info,
                "action": action,
            })

    # Write results
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Results written to {RESULTS_PATH}")
    print("\n--- SUMMARY ---")
    for r in results:
        print(f"  {r['difficulty']:8s}  {r['task_id']:20s}  reward={r['reward']:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run OpenAI baseline against the OpenEnv environment.")
    parser.add_argument(
        "--env-url",
        default="http://localhost:7860",
        help="Base URL of the running environment (default: http://localhost:7860)",
    )
    args = parser.parse_args()
    run_baseline(args.env_url)
