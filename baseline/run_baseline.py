"""
Baseline inference script.

Runs a Gemini agent against all three task difficulties and records scores.
Requires the environment server to be running (local or HuggingFace Spaces).

Usage:
    export GEMINI_API_KEY=your_key_here
    python baseline/run_baseline.py --env-url http://localhost:7860
    python baseline/run_baseline.py --env-url https://your-space.hf.space

Output: baseline/results.json
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import httpx
from google import genai
from google.genai import types
from google.api_core.exceptions import ResourceExhausted

DIFFICULTIES = ["easy", "medium", "hard"]
RESULTS_PATH = Path(__file__).parent / "results.json"

# Delay between difficulty runs to stay under free-tier RPM limit (5 req/min)
INTER_RUN_DELAY = 15  # seconds — conservative buffer between the 3 runs

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


def _parse_retry_delay(error: ResourceExhausted) -> int:
    """
    Extract the retry_delay seconds from the Gemini error message if present.
    Falls back to 65 seconds (safe default above free-tier 1-min window).
    """
    match = re.search(r"retry_delay\s*\{[^}]*seconds:\s*(\d+)", str(error))
    if match:
        return int(match.group(1)) + 5  # add 5s buffer
    return 65


def call_agent(client: genai.Client, observation: dict, max_retries: int = 5) -> dict:
    full_prompt = SYSTEM_PROMPT + "\n\n" + build_user_prompt(observation)

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=full_prompt,
                config=types.GenerateContentConfig(temperature=0),
            )
            raw = response.text.strip()

            # Strip markdown code fences if model adds them anyway
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            return json.loads(raw)

        except ResourceExhausted as e:
            if attempt == max_retries - 1:
                print("  ERROR: Max retries reached. Daily Free Tier quota may be exhausted.", file=sys.stderr)
                raise e

            wait_time = _parse_retry_delay(e)
            print(
                f"  [Rate Limit] Free Tier quota exceeded. "
                f"Sleeping {wait_time}s before retrying "
                f"(Attempt {attempt + 1}/{max_retries})...",
                file=sys.stderr,
            )
            time.sleep(wait_time)

    raise RuntimeError("call_agent: exhausted retries without raising")


def run_baseline(env_url: str) -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    results = []

    with httpx.Client(base_url=env_url, timeout=30.0) as http:
        # Health check
        health = http.get("/")
        if health.status_code != 200:
            print(f"ERROR: Environment at {env_url} is not responding.", file=sys.stderr)
            sys.exit(1)
        print(f"Environment healthy: {env_url}\n")

        for i, difficulty in enumerate(DIFFICULTIES):
            # Polite delay between runs to stay under free-tier RPM limit
            if i > 0:
                print(f"  [Rate limit guard] Waiting {INTER_RUN_DELAY}s before next run...\n")
                time.sleep(INTER_RUN_DELAY)

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
    parser = argparse.ArgumentParser(description="Run Gemini baseline against the OpenEnv environment.")
    parser.add_argument(
        "--env-url",
        default="http://localhost:7860",
        help="Base URL of the running environment (default: http://localhost:7860)",
    )
    args = parser.parse_args()
    run_baseline(args.env_url)
