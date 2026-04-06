#!/usr/bin/env python3
"""
Baseline Inference Script for Email Triage Environment
========================================================

Uses OpenAI Chat API to run an agent against the environment.
Outputs structured logs in [START], [STEP], [END] format.

Environment Variables:
  - API_BASE_URL (default: https://router.huggingface.co/v1)
  - MODEL_NAME (default: Qwen/Qwen2.5-72B-Instruct)
  - HF_TOKEN or OPENAI_API_KEY (required)
"""

import asyncio
import json
import os
import sys
import textwrap
from typing import Optional

from openai import OpenAI

# Import environment
try:
    from email_triage_env import EmailTriageEnv, Action
except ImportError:
    print("[ERROR] Failed to import email_triage_env. Ensure it's in Python path.", file=sys.stderr)
    sys.exit(1)

# Configuration from environment
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY")

if not API_KEY:
    print("[ERROR] Missing API key. Set HF_TOKEN or OPENAI_API_KEY.", file=sys.stderr)
    sys.exit(1)

# Task configuration
TASK_NAME = os.getenv("TASK_NAME", "multiclass_medium")
BENCHMARK = os.getenv("BENCHMARK", "email-triage-v1")
MAX_STEPS = 20
TEMPERATURE = 0.7
MAX_TOKENS = 200

# Parse task name: format is "task_type_difficulty" or "task_difficulty"
def parse_task_name(name: str):
    """Parse task name like 'binary_easy' into (task_type, difficulty)."""
    parts = name.rsplit("_", 1)
    if len(parts) == 2:
        task_type, difficulty = parts
        if task_type in ["binary", "multiclass", "routing"]:
            return task_type, difficulty
        # Try as all task_type
        task_type_full = name.rsplit("_", 1)[0]
        if "_" in task_type_full:
            return task_type_full.split("_")[0], parts[-1]
    return "multiclass", "medium"

TASK_TYPE, DIFFICULTY = parse_task_name(TASK_NAME)

SYSTEM_PROMPT = textwrap.dedent(
    f"""
    You are an email triage AI agent. Your task is to classify incoming emails and route them appropriately.
    
    Current Task: {TASK_NAME}
    Task Type: {TASK_TYPE}
    Difficulty: {DIFFICULTY}
    
    Email Classification Categories:
    - "spam": Unsolicited, malicious, or unwanted emails
    - "urgent": Requires immediate attention (VP requests, critical incidents, escalations)
    - "important": Needs response but not immediately (meetings, proposals, updates)
    - "routine": Informational only, low priority (newsletters, reminders, announcements)
    
    For each email presented:
    1. Read the email carefully
    2. Classify it into one of the 4 categories
    3. Provide confidence (0.0-1.0) - how sure you are
    4. Decide if response is needed
    5. Optionally route to department (support, sales, engineering, hr)
    
    Be strategic:
    - Spam emails should get low confidence if ambiguous
    - Urgent emails need high confidence
    - Consider sender (internal vs external), subject urgency, and content
    - Calibrate your confidence to your accuracy
    
    Reply ONLY with a JSON object, no other text. Example:
    {{"classification": "urgent", "confidence": 0.95, "needs_response": true, "route_to": "support"}}
    """
).strip()


def log_start(task: str, env: str, model: str) -> None:
    """Log episode start."""
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    """Log step execution."""
    error_val = error if error else "null"
    done_val = str(done).lower()
    # Truncate action for logging
    action_display = action[:100] if len(action) > 100 else action
    print(
        f"[STEP] step={step} action={action_display} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: list) -> None:
    """Log episode end."""
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


def build_user_prompt(step: int, email_data: dict, history: list) -> str:
    """Build user prompt with email info."""
    history_block = "\n".join(history[-3:]) if history else "None"
    
    email_str = f"""
    Email #{step}:
    FROM: {email_data['sender']}
    SUBJECT: {email_data['subject']}
    INTERNAL: {email_data['is_internal']}
    ATTACHMENTS: {email_data['has_attachment']}
    LENGTH: {email_data['word_count']} words
    
    BODY:
    {email_data['body'][:500]}
    """
    
    if len(history) > 0:
        history_str = f"\n\nRecent classifications:\n{history_block}"
    else:
        history_str = ""
    
    return textwrap.dedent(email_str).strip() + history_str


def parse_model_response(response_text: str) -> Optional[dict]:
    """Parse model response as JSON."""
    try:
        response_text = response_text.strip()
        # Try to extract JSON if there's extra text
        if "{" in response_text and "}" in response_text:
            start = response_text.index("{")
            end = response_text.rindex("}") + 1
            json_str = response_text[start:end]
        else:
            json_str = response_text
        
        parsed = json.loads(json_str)
        
        # Validate and fill defaults
        classification = parsed.get("classification", "routine")
        if classification not in ["spam", "urgent", "important", "routine"]:
            classification = "routine"
        
        confidence = float(parsed.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))
        
        needs_response = bool(parsed.get("needs_response", False))
        route_to = parsed.get("route_to", None)
        
        return {
            "classification": classification,
            "confidence": confidence,
            "needs_response": needs_response,
            "route_to": route_to,
        }
    except Exception as e:
        print(f"[DEBUG] Failed to parse response: {e}", file=sys.stderr)
        return None


async def run_episode() -> tuple[bool, float, int, list]:
    """
    Run one complete episode.
    Returns: (success, score, total_steps, rewards)
    """
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    # Initialize environment
    env = EmailTriageEnv(
        task=TASK_TYPE,
        difficulty=DIFFICULTY,
        max_steps=MAX_STEPS,
    )
    
    history = []
    rewards = []
    steps_taken = 0
    last_error = None

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        # Reset environment
        reset_result = await env.reset()
        current_obs = reset_result["observation"]
        
        if current_obs is None or current_obs.current_email is None:
            raise RuntimeError("Failed to reset environment")

        for step in range(1, MAX_STEPS + 1):
            if current_obs is None or current_obs.current_email is None:
                break

            email_data = current_obs.current_email.dict()
            
            # Get model response
            user_prompt = build_user_prompt(step, email_data, history)
            
            try:
                completion = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                    timeout=30,
                )
                
                response_text = (completion.choices[0].message.content or "").strip()
                action_dict = parse_model_response(response_text)
                
                if action_dict is None:
                    action_dict = {
                        "classification": "routine",
                        "confidence": 0.3,
                        "needs_response": False,
                        "route_to": None,
                    }
                
            except Exception as e:
                last_error = str(e)
                print(f"[DEBUG] Model call failed: {e}", file=sys.stderr)
                action_dict = {
                    "classification": "routine",
                    "confidence": 0.1,
                    "needs_response": False,
                    "route_to": None,
                }

            # Create action
            action = Action(**action_dict)
            action_str = f"classify={action.classification}, conf={action.confidence:.2f}"

            # Execute step
            try:
                step_result = await env.step(action)
                reward = step_result.get("reward", 0.0)
                done = step_result.get("done", False)
            except Exception as e:
                last_error = str(e)
                reward = 0.0
                done = False

            rewards.append(reward)
            steps_taken = step

            log_step(step=step, action=action_str, reward=reward, done=done, error=last_error)

            history.append(f"Step {step}: {action_str}, reward={reward:.2f}")

            # Get next observation
            if not done:
                current_obs = step_result.get("observation")
            else:
                current_obs = None
                break

        # Grade the task
        task_result = env.grade_task()
        success = task_result.success
        score = task_result.final_score

    except Exception as e:
        print(f"[DEBUG] Episode error: {e}", file=sys.stderr)
        success = False
        score = 0.0
        steps_taken = 0

    finally:
        try:
            await env.close()
        except Exception as e:
            print(f"[DEBUG] Env close error: {e}", file=sys.stderr)

    log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return success, score, steps_taken, rewards


async def main():
    """Main entry point."""
    try:
        success, score, steps, rewards = await run_episode()
        
        # Return exit code based on success
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("[DEBUG] Interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"[DEBUG] Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
