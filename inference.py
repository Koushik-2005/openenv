#!/usr/bin/env python3
"""
Baseline Inference Script for Email Triage Environment
========================================================

Runs and grades all hackathon tasks by default.
Outputs structured logs in [START], [STEP], [END] format for each task.

Environment Variables:
  - API_BASE_URL (default: https://router.huggingface.co/v1)
  - MODEL_NAME (default: Qwen/Qwen2.5-72B-Instruct)
    - HF_TOKEN or OPENAI_API_KEY (optional; uses deterministic fallback if missing)
    - TASK_NAME (optional; run a single task id like binary_easy, otherwise runs all)
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

# Task configuration
TASK_NAME = os.getenv("TASK_NAME", "all")
BENCHMARK = os.getenv("BENCHMARK", "email-triage-v1")
TEMPERATURE = 0.7
MAX_TOKENS = 200
TASKS = [
    {
        "task_id": "binary_easy",
        "task_type": "binary",
        "difficulty": "easy",
        "max_steps": 10,
    },
    {
        "task_id": "multiclass_medium",
        "task_type": "multiclass",
        "difficulty": "medium",
        "max_steps": 20,
    },
    {
        "task_id": "routing_hard",
        "task_type": "routing",
        "difficulty": "hard",
        "max_steps": 20,
    },
]

# Parse task name: format is "task_type_difficulty" or "task_difficulty"
def parse_task_name(name: str):
    """Parse task name like 'binary_easy' into (task_type, difficulty)."""
    parts = name.rsplit("_", 1)
    if len(parts) == 2:
        task_type, difficulty = parts
        if task_type in ["binary", "multiclass", "routing"]:
            return task_type, difficulty
    if name in ["binary", "multiclass", "routing"]:
        return name, "medium"
    return "multiclass", "medium"


def build_system_prompt(task_name: str, task_type: str, difficulty: str) -> str:
    """Build task-specific system prompt."""
    return textwrap.dedent(
        f"""
    You are an email triage AI agent. Your task is to classify incoming emails and route them appropriately.
    
    Current Task: {task_name}
    Task Type: {task_type}
    Difficulty: {difficulty}
    
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


def select_tasks(task_name: str) -> list[dict]:
    """Return selected task configs. Defaults to all tasks for validator compatibility."""
    normalized = (task_name or "").strip().lower()
    if normalized in {"", "all", "*", "all_tasks"}:
        return TASKS

    for task in TASKS:
        if task["task_id"] == normalized:
            return [task]

    parsed_type, parsed_difficulty = parse_task_name(normalized)
    for task in TASKS:
        if task["task_type"] == parsed_type and task["difficulty"] == parsed_difficulty:
            return [task]

    print(f"[DEBUG] Unknown TASK_NAME='{task_name}', running all tasks.", file=sys.stderr)
    return TASKS


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


def heuristic_action(email_data: dict, task_type: str) -> dict:
    """Deterministic fallback policy when no API key/model call is available."""
    text = f"{email_data.get('subject', '')} {email_data.get('body', '')}".lower()

    spam_keywords = [
        "free",
        "winner",
        "click",
        "offer",
        "money",
        "dating",
        "work from home",
        "act now",
    ]
    urgent_keywords = [
        "urgent",
        "critical",
        "immediate",
        "asap",
        "security breach",
        "production",
        "down",
        "escalation",
    ]
    important_keywords = [
        "proposal",
        "review",
        "meeting",
        "roadmap",
        "planning",
        "project",
        "approved",
    ]

    if any(k in text for k in spam_keywords):
        classification = "spam"
        confidence = 0.85
    elif any(k in text for k in urgent_keywords):
        classification = "urgent"
        confidence = 0.8
    elif any(k in text for k in important_keywords):
        classification = "important"
        confidence = 0.7
    else:
        classification = "routine"
        confidence = 0.6

    # Binary mode is spam vs non-spam in this environment; map non-spam to routine.
    if task_type == "binary" and classification != "spam":
        classification = "routine"

    route_to = None
    if classification != "spam" and task_type == "routing":
        sender = (email_data.get("sender") or "").lower()
        if "support" in text or "issue" in text or "ticket" in text:
            route_to = "support"
        elif "sales" in text or "proposal" in text or "pricing" in text:
            route_to = "sales"
        elif "bug" in text or "api" in text or "engineering" in text:
            route_to = "engineering"
        elif "hr" in text or "policy" in text or "leave" in text or "benefit" in text:
            route_to = "hr"
        elif sender.endswith("@company.com"):
            route_to = "engineering"

    return {
        "classification": classification,
        "confidence": confidence,
        "needs_response": classification in {"urgent", "important"},
        "route_to": route_to,
    }


def get_action(
    client: Optional[OpenAI],
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    email_data: dict,
    task_type: str,
) -> tuple[dict, Optional[str]]:
    """Return action dict and optional error string."""
    if client is None:
        return heuristic_action(email_data, task_type), "null"

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            timeout=30,
        )

        response_text = (completion.choices[0].message.content or "").strip()
        action_dict = parse_model_response(response_text)
        if action_dict is None:
            return heuristic_action(email_data, task_type), "parse_error"
        return action_dict, "null"
    except Exception as e:
        print(f"[DEBUG] Model call failed: {e}", file=sys.stderr)
        return heuristic_action(email_data, task_type), str(e)


async def run_single_task(task_cfg: dict, client: Optional[OpenAI]) -> tuple[bool, float, int, list]:
    """
    Run one complete episode for a specific task.
    Returns: (success, score, steps, rewards)
    """
    task_name = task_cfg["task_id"]
    task_type = task_cfg["task_type"]
    difficulty = task_cfg["difficulty"]
    max_steps = int(task_cfg["max_steps"])
    system_prompt = build_system_prompt(task_name, task_type, difficulty)
    
    # Initialize environment
    env = EmailTriageEnv(
        task=task_type,
        difficulty=difficulty,
        max_steps=max_steps,
    )
    
    history = []
    rewards = []
    steps_taken = 0
    success = False
    score = 0.0
    last_error: Optional[str] = None

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        # Reset environment
        reset_result = await env.reset()
        current_obs = reset_result["observation"]
        
        if current_obs is None or current_obs.current_email is None:
            raise RuntimeError("Failed to reset environment")

        for step in range(1, max_steps + 1):
            if current_obs is None or current_obs.current_email is None:
                break

            if hasattr(current_obs.current_email, "model_dump"):
                email_data = current_obs.current_email.model_dump()
            else:
                email_data = current_obs.current_email.dict()
            
            # Get model response
            user_prompt = build_user_prompt(step, email_data, history)
            action_dict, error_text = get_action(
                client=client,
                model_name=MODEL_NAME,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                email_data=email_data,
                task_type=task_type,
            )
            if error_text and error_text != "null":
                last_error = error_text

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
                done = True

            rewards.append(reward)
            steps_taken = step

            log_step(
                step=step,
                action=action_str,
                reward=reward,
                done=done,
                error=last_error,
            )

            history.append(f"Step {step}: {action_str}, reward={reward:.2f}")
            last_error = None

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
        if steps_taken == 0:
            steps_taken = 1

    finally:
        try:
            await env.close()
        except Exception as e:
            print(f"[DEBUG] Env close error: {e}", file=sys.stderr)

    log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return success, score, steps_taken, rewards


async def run_all_tasks() -> tuple[bool, float]:
    """Run selected tasks (defaults to all 3 tasks for hackathon validator compatibility)."""
    selected_tasks = select_tasks(TASK_NAME)
    client: Optional[OpenAI] = None

    if API_KEY:
        client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    else:
        print("[DEBUG] No API key found, using deterministic fallback policy.", file=sys.stderr)

    results = []
    for task_cfg in selected_tasks:
        task_success, task_score, _, _ = await run_single_task(task_cfg, client)
        results.append((task_cfg["task_id"], task_success, task_score))

    overall_success = all(s for _, s, _ in results) if results else False
    avg_score = sum(score for _, _, score in results) / len(results) if results else 0.0
    return overall_success, avg_score


async def main():
    """Main entry point."""
    try:
        await run_all_tasks()
        # Exit 0 after successfully producing task logs.
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("[DEBUG] Interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"[DEBUG] Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
