"""
Baseline inference script.

Runs a Gemini agent against all three task difficulties and records scores.
Requires the environment server to be running (local or HuggingFace Spaces).

Usage:
    export GEMINI_API_KEY=your_key_here
    python baseline/run_baseline.py --env-url http://localhost:7860
    python baseline/run_baseline.py --env-url https://your-space.hf.space
    python baseline/run_baseline.py --env-url https://your-space.hf.space --model gemini-2.5-flash-lite

Output: baseline/results.json
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

DIFFICULTIES = ["easy", "medium", "hard"]
RESULTS_PATH = Path(__file__).parent / "results.json"

DEFAULT_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are a senior software engineer performing code review and security auditing.

IMPORTANT: Lines are numbered starting at 1. Count each line of code carefully.
The first line of the code snippet is line 1, the second is line 2, and so on.
Empty lines and comment lines count toward line numbering.

Analyze the provided code carefully and respond ONLY with a valid JSON object in this exact format:
{
  "flagged_lines": [<list of integer line numbers (1-indexed) where bugs exist>],
  "findings": [
    { "type": "<vulnerability type, e.g. sql_injection, hardcoded_secret, xss>", "description": "<explanation>" }
  ],
  "review_text": "<structured code review: include severity labels (critical/high/medium/low), line references (line N or LN), actionable recommendations (should/must/recommend), and category labels (bug/security/vulnerability/style/performance)>"
}

For flagged_lines: flag the exact line numbers where bugs or errors occur.
For findings: use snake_case type names like sql_injection, hardcoded_secret, xss, path_traversal, insecure_deserialization.
For review_text: always reference specific line numbers, assign severity, use actionable language, and categorize issues.

Respond with JSON only. No markdown, no explanation, no code fences."""


def build_user_prompt(observation: dict) -> str:
    # Add explicit line numbers to the code snippet so the model can reference them accurately
    code_lines = observation["code_snippet"].splitlines()
    numbered = "\n".join(f"{i+1}: {line}" for i, line in enumerate(code_lines))
    return (
        f"Task: {observation['instructions']}\n\n"
        f"Code (line numbers shown for reference):\n{numbered}"
    )


def call_agent(model: genai.GenerativeModel, observation: dict, max_retries: int = 5) -> dict:
    full_prompt = SYSTEM_PROMPT + "\n\n" + build_user_prompt(observation)

    for attempt in range(max_retries):
        try:
            response = model.generate_content(full_prompt)
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
                print(
                    "  ERROR: Max retries reached. Daily Free Tier quota may be exhausted.",
                    file=sys.stderr,
                )
                raise e

            wait_time = 45
            print(
                f"  [Rate Limit] Free Tier quota exceeded. "
                f"Sleeping {wait_time}s before retry (attempt {attempt + 1}/{max_retries})...",
                file=sys.stderr,
            )
            time.sleep(wait_time)

        except json.JSONDecodeError as e:
            print(f"  WARNING: JSON parse failed on attempt {attempt + 1}: {e}", file=sys.stderr)
            if attempt == max_retries - 1:
                raise

    # Should not be reached, but satisfy type checker
    return {"flagged_lines": [], "findings": [], "review_text": ""}


def run_baseline(env_url: str, model_name: str) -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=genai.types.GenerationConfig(
            temperature=0,  # Deterministic output
        ),
    )
    print(f"Model: {model_name}")

    results = []

    with httpx.Client(base_url=env_url, timeout=30.0) as http:
        # Health check
        health = http.get("/")
        if health.status_code != 200:
            print(f"ERROR: Environment at {env_url} is not responding.", file=sys.stderr)
            sys.exit(1)
        print(f"Environment healthy: {env_url}\n")

        for i, difficulty in enumerate(DIFFICULTIES):
            print(f"Running difficulty: {difficulty}")

            # Reset
            reset_resp = http.post("/reset", json={"task_difficulty": difficulty})
            reset_resp.raise_for_status()
            observation = reset_resp.json()
            print(f"  Episode: {observation['task_id']}")

            # Agent inference
            try:
                action = call_agent(model, observation)
            except Exception as e:
                print(f"  ERROR: Agent call failed: {e}", file=sys.stderr)
                action = {"flagged_lines": [], "findings": [], "review_text": ""}

            # Step
            step_resp = http.post("/step", json=action)
            step_resp.raise_for_status()
            result = step_resp.json()

            reward = result["reward"]
            info = result.get("info", {})
            print(f"  Reward: {reward:.4f}  Info: {info}")

            results.append({
                "difficulty": difficulty,
                "task_id": observation["task_id"],
                "reward": reward,
                "info": info,
                "action": action,
            })

            # Rate limit guard between runs (skip after last one)
            if i < len(DIFFICULTIES) - 1:
                print("  [Rate limit guard] Waiting 15s before next run...")
                time.sleep(15)

        print()

    # Write results
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Results written to {RESULTS_PATH}")
    print("\n--- SUMMARY ---")
    for r in results:
        print(f"  {r['difficulty']:8s}  {r['task_id']:20s}  reward={r['reward']:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run Gemini baseline against the OpenEnv environment."
    )
    parser.add_argument(
        "--env-url",
        default="http://localhost:7860",
        help="Base URL of the running environment (default: http://localhost:7860)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Gemini model name to use (default: {DEFAULT_MODEL}). "
             "Use 'gemini-2.5-flash-lite' if you hit quota limits on the default.",
    )
    args = parser.parse_args()
    run_baseline(args.env_url, args.model)
