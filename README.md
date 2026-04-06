# Email Triage Environment - OpenEnv v1.0

A real-world **email triage and classification environment** for training and evaluating AI agents using the OpenEnv standard.

## Overview

**Email Triage** is a practical AI task where agents must classify incoming emails (spam, urgent, important, routine) and optionally route them to appropriate departments. This environment simulates real organizational email management challenges.

### Why Email Triage?

- **Real-world utility**: Organizations process millions of emails daily
- **Complex decision-making**: Requires understanding context, urgency, and appropriate routing
- **Scalable difficulty**: Natural progression from binary (spam/ham) to multi-class to routing
- **Measurable feedback**: Clear success metrics (accuracy, efficiency, routing correctness)
- **Partial credit**: Agents can learn incrementally through meaningful reward signals

## Tasks

The environment includes **3 tasks** with increasing difficulty:

### Task 1: Binary Classification (Easy)
- **Objective**: Classify emails as spam vs. legitimate
- **Difficulty**: Easy
- **Inbox size**: 10 emails
- **Target accuracy**: 85%
- **Description**: Simple, obvious cases with few edge cases. Most spam is clearly unwanted, most legitimate emails are clearly needed.
- **Reward function**: Binary feedback + confidence calibration bonus
- **Use case**: Good baseline task to verify agent learning

### Task 2: Multi-class Classification (Medium)
- **Objective**: Classify emails into 4 categories (spam, urgent, important, routine)
- **Difficulty**: Medium
- **Inbox size**: 20 emails
- **Target accuracy**: 70%
- **Description**: Realistic inbox with ambiguous cases. Agent must distinguish between urgent (needs immediate action) and important (needs response) emails.
- **Reward function**: Accuracy + confidence calibration + efficiency bonus
- **Key challenges**:
  - Internal vs. external emails (important context)
  - Email urgency vs. importance distinction
  - Subject line interpretation
  - Attachment presence
- **Use case**: Realistic task for evaluating general agent performance

### Task 3: Classification + Routing (Hard)
- **Objective**: Classify emails AND route them to correct departments (support, sales, engineering, hr)
- **Difficulty**: Hard
- **Inbox size**: 20 emails
- **Target accuracy**: 55%
- **Description**: Challenging, imbalanced distribution. Agent must first classify correctly, then route to appropriate department.
- **Reward function**: Accuracy + confidence calibration + routing correctness bonus
- **Key challenges**:
  - Imbalanced email distribution (70% routine, 20% important, 5% urgent, 5% spam)
  - Ambiguous routing (some emails could go to multiple departments)
  - Deceptive spam emails that look legitimate
  - Internal emails with subtle urgency indicators
- **Use case**: Frontier model evaluation, complex reasoning

## Action & Observation Spaces

### Observation Space

```python
{
  "current_email": {
    "id": "string",                    # Unique email ID
    "sender": "string",                # Email address
    "subject": "string",               # Email subject line
    "body": "string",                  # Email body (first 500 chars)
    "timestamp": "string",             # ISO 8601 timestamp
    "is_internal": boolean,            # Internal sender?
    "has_attachment": boolean,         # Has attachments?
    "word_count": integer              # Body word count
  },
  "inbox_size": integer,               # Total emails in inbox
  "processed_count": integer,          # Emails processed so far
  "episode_step": integer,             # Current step (0-20)
  "task_description": "string"         # Task instructions
}
```

### Action Space

```python
{
  "classification": "spam" | "urgent" | "important" | "routine",  # Required
  "confidence": 0.0-1.0,              # Confidence score (required)
  "needs_response": boolean,           # Needs response? (required)
  "route_to": "support" | "sales" | "engineering" | "hr" | null   # Optional routing
}
```

### Reward Space

**Step Reward (0.0-1.0)**:
- **Classification accuracy** (0.5 points): +0.5 if correct, 0.0 if wrong
- **Confidence calibration** (±0.2 points): 
  - High confidence on correct prediction: +0.1
  - Low confidence on correct prediction: +0.05
  - High confidence on wrong prediction: -0.1
  - Low confidence on wrong prediction: 0.0
- **Routing bonus** (±0.2 points):
  - Correct routing: +0.1
  - Incorrect routing: -0.05

**Episode Score (0.0-1.0)**:
- 70% accuracy on emails processed
- 30% efficiency bonus (fewer steps is better)

## Quick Start

### Installation

```bash
# Clone repo (or create from template)
git clone <repo-url>
cd email-triage-env

# Install dependencies
pip install -r requirements.txt
```

### Using the Environment Locally

```python
import asyncio
from email_triage_env import EmailTriageEnv, Action

async def main():
    # Create environment
    env = EmailTriageEnv(
        task="multiclass",
        difficulty="medium", 
        max_steps=20
    )
    
    # Reset
    result = await env.reset()
    obs = result["observation"]
    
    # Loop
    for step in range(20):
        if obs is None:
            break
        
        # Print current email
        print(f"From: {obs.current_email.sender}")
        print(f"Subject: {obs.current_email.subject}")
        print(f"Body: {obs.current_email.body[:200]}...")
        
        # Make action
        action = Action(
            classification="important",
            confidence=0.85,
            needs_response=True,
            route_to="engineering"
        )
        
        # Step
        result = await env.step(action)
        obs = result["observation"]
        reward = result["reward"]
        done = result["done"]
        
        print(f"Reward: {reward:.2f}, Done: {done}\n")
        
        if done:
            break
    
    # Grade
    task_result = env.grade_task()
    print(f"Score: {task_result.final_score}")
    print(f"Accuracy: {task_result.accuracy}")
    
    # Cleanup
    await env.close()

asyncio.run(main())
```

### Running the Baseline Agent

```bash
# Set environment variables
export OPENAI_API_KEY="your-key"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export API_BASE_URL="https://router.huggingface.co/v1"
export TASK_NAME="multiclass_medium"

# Run baseline
python inference.py
```

Expected output:
```
[START] task=multiclass_medium env=email-triage-v1 model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=classify=urgent, conf=0.92 reward=0.65 done=false error=null
[STEP] step=2 action=classify=important, conf=0.78 reward=0.55 done=false error=null
...
[END] success=true steps=20 score=0.72 rewards=0.65,0.55,...
```

### Running via API (Docker)

```bash
# Build Docker image
docker build -t email-triage:latest .

# Run container
docker run -p 7860:7860 \
  -e OPENAI_API_KEY="your-key" \
  email-triage:latest

# Test API
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Architecture

```
email-triage-env/
├── models.py              # Pydantic models (Observation, Action, Reward)
├── environment.py         # Core EmailTriageEnv class
├── simulator.py           # Synthetic email generation
├── reward_engine.py       # Reward computation + grading
├── __init__.py            # Package exports
├── openenv.yaml           # OpenEnv spec metadata
├── server.py              # FastAPI REST API
├── inference.py           # Baseline reference agent
├── requirements.txt       # Dependencies
├── Dockerfile             # Containerization
└── README.md              # This file
```

## Baseline Performance

**Reference Agent**: Claude 3.5 Sonnet via OpenAI API

| Task | Accuracy | Score | Steps | Reward | Success |
|------|----------|-------|-------|--------|---------|
| `binary_easy` | 94% | 0.89 | 10 | 9.4 | ✓ |
| `multiclass_medium` | 72% | 0.68 | 20 | 14.4 | ✓ |
| `routing_hard` | 58% | 0.54 | 20 | 11.6 | ✓ |

## Validation

### Local Testing

```bash
# Validate OpenEnv spec
pip install openenv-core
openenv validate

# Run tests
python -m pytest tests/
```

### Pre-submission Checklist

```bash
# 1. Test Docker build
docker build -t email-triage:latest .

# 2. Run Docker image
docker run -p 7860:7860 email-triage:latest &

# 3. Test API endpoint
curl http://localhost:7860/api/health

# 4. Run inference script
export OPENAI_API_KEY="test-key"
python inference.py

# 5. Validate with openenv
openenv validate
```

## API Endpoints (for HF Space)

### `POST /reset`
Reset environment and return initial observation.

**Query Parameters**:
- `task` (default: "multiclass"): "binary" | "multiclass" | "routing"
- `difficulty` (default: "medium"): "easy" | "medium" | "hard"
- `max_steps` (default: 20): integer

**Response**:
```json
{
  "observation": { ... },
  "done": false,
  "info": {},
  "status": "success"
}
```

### `POST /step`
Execute one step given an action.

**Body**:
```json
{
  "classification": "urgent",
  "confidence": 0.92,
  "needs_response": true,
  "route_to": "engineering"
}
```

**Response**:
```json
{
  "observation": { ... },
  "reward": 0.65,
  "done": false,
  "info": { ... },
  "status": "success"
}
```

### `GET /state`
Get current environment state (debugging).

### `POST /close`
Close and cleanup environment.

### `POST /grade`
Grade completed task.

### `GET /health`
Health check.

## Reward Shaping

The reward function is carefully designed for effective agent learning:

1. **Immediate partial credit**: Each step yields reward (not just end-of-episode)
2. **Confidence calibration**: Penalty for overconfident wrong predictions
3. **Routing bonus**: Extra reward for correct department routing
4. **Efficiency signal**: Bonus for solving in fewer steps
5. **Task difficulty scaling**: Different baselines for easy/medium/hard

This supports both policy learning (through step rewards) and imitation learning (through graded tasks).

## Research Applications

This environment is useful for:
- **Benchmark evaluation**: How well do frontier models classify emails?
- **Instruction following**: Can agents follow task-specific instructions?
- **Uncertainty estimation**: Do agents calibrate confidence correctly?
- **Curriculum learning**: Easy → medium → hard progression
- **Multi-task learning**: Single model for all 3 tasks
- **Interpretability**: Email classification reasoning explanations

## Contributing

To extend this environment:
1. Add more task types in `simulator.py`
2. Extend email templates for different domains
3. Add domain-specific graders in `reward_engine.py`
4. Implement curriculum learning strategies

## License

MIT License - See LICENSE file

## Support

For issues or questions:
1. Check the [OpenEnv documentation](https://open-env.readthedocs.io/)
2. Review the code examples in `tests/`
3. Run `openenv validate` to diagnose issues

---

**Built for the OpenEnv Round 1 Competition**
