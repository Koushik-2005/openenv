"""
API Server for Email Triage Environment
Implements OpenEnv spec endpoints for HF Space deployment.

Endpoints:
  POST /reset - Initialize environment
  POST /step - Execute action step
  GET /state - Get current state
  POST /close - Cleanup
  GET /health - Health check
"""

import asyncio
import json
import logging
from typing import Optional

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
except ImportError:
    print("Installing FastAPI...")
    import subprocess
    subprocess.check_call(["pip", "install", "fastapi", "uvicorn"])
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn

from email_triage_env import EmailTriageEnv, Action
from email_triage_env.models import Observation

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Email Triage Environment API",
    description="OpenEnv-compliant Email Triage API",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global environment instance
env: Optional[EmailTriageEnv] = None
env_lock = asyncio.Lock()

TASKS_WITH_GRADERS = [
    {
        "id": "binary_easy",
        "name": "binary_easy",
        "description": "Binary classification (spam vs legitimate) on obvious cases",
        "difficulty": "easy",
        "task_type": "binary",
        "max_steps": 10,
        "grader": {
            "type": "accuracy_threshold",
            "success_threshold": 0.85,
            "scoring": {
                "method": "weighted_accuracy_efficiency",
                "range": [0.0, 1.0],
                "weights": {"accuracy": 0.7, "efficiency": 0.3},
            },
        },
    },
    {
        "id": "multiclass_medium",
        "name": "multiclass_medium",
        "description": "Multi-class classification with moderate difficulty",
        "difficulty": "medium",
        "task_type": "multiclass",
        "max_steps": 20,
        "grader": {
            "type": "accuracy_threshold",
            "success_threshold": 0.70,
            "scoring": {
                "method": "weighted_accuracy_efficiency",
                "range": [0.0, 1.0],
                "weights": {"accuracy": 0.7, "efficiency": 0.3},
            },
        },
    },
    {
        "id": "routing_hard",
        "name": "routing_hard",
        "description": "Full task: classify and route emails",
        "difficulty": "hard",
        "task_type": "routing",
        "max_steps": 20,
        "grader": {
            "type": "accuracy_threshold",
            "success_threshold": 0.55,
            "scoring": {
                "method": "weighted_accuracy_efficiency",
                "range": [0.0, 1.0],
                "weights": {"accuracy": 0.7, "efficiency": 0.3},
            },
        },
    },
]


async def get_or_create_env(**kwargs) -> EmailTriageEnv:
    """Get or create environment instance."""
    global env
    async with env_lock:
        if env is None:
            env = EmailTriageEnv(**kwargs)
    return env


def serialize_observation(obs: Observation) -> dict:
    """Convert Observation to JSON-serializable dict."""
    if obs is None:
        return None
    
    email_dict = None
    if obs.current_email:
        if hasattr(obs.current_email, "model_dump"):
            email_dict = obs.current_email.model_dump()
        else:
            email_dict = obs.current_email.dict()
    
    return {
        "current_email": email_dict,
        "inbox_size": obs.inbox_size,
        "processed_count": obs.processed_count,
        "episode_step": obs.episode_step,
        "task_description": obs.task_description,
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "email-triage-v1",
        "version": "1.0.0",
    }


@app.get("/metadata")
async def metadata():
    """Expose environment metadata, including task graders, for validator discovery."""
    return {
        "name": "email-triage-v1",
        "version": "1.0.0",
        "description": "Email triage and routing environment with progressive task difficulty.",
        "scoring_range": [0.0, 1.0],
        "tasks": TASKS_WITH_GRADERS,
    }


@app.get("/tasks")
async def list_tasks():
    """List all supported tasks with grader metadata."""
    return {
        "tasks": TASKS_WITH_GRADERS,
        "count": len(TASKS_WITH_GRADERS),
    }


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get one task by id with grader metadata."""
    for task in TASKS_WITH_GRADERS:
        if task["id"] == task_id or task["name"] == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")


@app.get("/schema")
async def schema():
    """Return action and observation schemas used by this environment."""
    return {
        "action_schema": Action.model_json_schema(),
        "observation_schema": Observation.model_json_schema(),
        "reward": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
        },
    }


@app.post("/reset")
async def reset(request: Request):
    """
    Reset environment and return initial observation.
    
    Query params:
      - task: binary, multiclass, routing (default: multiclass)
      - difficulty: easy, medium, hard (default: medium)
      - max_steps: integer (default: 20)
    """
    try:
        # Parse query parameters
        task_param = request.query_params.get("task", "multiclass").strip().lower()
        difficulty = request.query_params.get("difficulty", "medium").strip().lower()
        max_steps = int(request.query_params.get("max_steps", "20"))

        task_aliases = {
            "binary_easy": ("binary", "easy"),
            "multiclass_medium": ("multiclass", "medium"),
            "routing_hard": ("routing", "hard"),
        }

        if task_param in task_aliases:
            task, difficulty = task_aliases[task_param]
        else:
            task = task_param
        
        # Validate inputs
        if task not in ["binary", "multiclass", "routing"]:
            task = "multiclass"
        if difficulty not in ["easy", "medium", "hard"]:
            difficulty = "medium"
        
        # Create new environment
        global env
        async with env_lock:
            env = EmailTriageEnv(
                task=task,
                difficulty=difficulty,
                max_steps=max_steps,
            )
        
        # Reset
        result = await env.reset()
        obs = result.get("observation")
        
        return {
            "observation": serialize_observation(obs),
            "done": result.get("done", False),
            "info": result.get("info", {}),
            "status": "success",
        }
        
    except Exception as e:
        logger.error(f"Reset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/step")
async def step(request: Request):
    """
    Execute one step in the environment.
    
    Body (JSON):
      - classification: "spam" | "urgent" | "important" | "routine"
      - confidence: float [0.0-1.0]
      - needs_response: boolean
      - route_to: string or null
    """
    try:
        global env
        if env is None:
            raise RuntimeError("Environment not initialized. Call /reset first.")
        
        # Parse request body
        body = await request.json()
        
        # Validate and create action
        action = Action(
            classification=body.get("classification", "routine"),
            confidence=float(body.get("confidence", 0.5)),
            needs_response=bool(body.get("needs_response", False)),
            route_to=body.get("route_to", None),
        )
        
        # Execute step
        result = await env.step(action)
        obs = result.get("observation")
        
        return {
            "observation": serialize_observation(obs),
            "reward": result.get("reward", 0.0),
            "done": result.get("done", False),
            "info": result.get("info", {}),
            "status": "success",
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid action: {str(e)}")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Step failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/state")
async def state():
    """Get current environment state."""
    try:
        global env
        if env is None:
            raise RuntimeError("Environment not initialized.")
        
        state_dict = await env.state()
        return {
            "state": state_dict,
            "status": "success",
        }
        
    except Exception as e:
        logger.error(f"State request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/close")
async def close():
    """Close and cleanup environment."""
    try:
        global env
        if env is not None:
            await env.close()
            env = None
        
        return {
            "status": "success",
            "message": "Environment closed",
        }
        
    except Exception as e:
        logger.error(f"Close failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/grade")
async def grade():
    """Grade the completed task."""
    try:
        global env
        if env is None:
            raise RuntimeError("Environment not initialized.")
        
        task_result = env.grade_task()
        
        return {
            "task_name": task_result.task_name,
            "success": task_result.success,
            "final_score": task_result.final_score,
            "accuracy": task_result.accuracy,
            "total_steps": task_result.total_steps,
            "total_reward": task_result.total_reward,
            "details": task_result.details or {},
            "status": "success",
        }
        
    except Exception as e:
        logger.error(f"Grade failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/docs")
async def docs():
    """API documentation."""
    return {
        "service": "Email Triage Environment API",
        "version": "1.0.0",
        "endpoints": {
            "POST /reset": "Reset environment (query: task, difficulty, max_steps)",
            "POST /step": "Execute action (body: Action JSON)",
            "GET /state": "Get current state",
            "POST /close": "Close environment",
            "POST /grade": "Grade task completion",
            "GET /health": "Health check",
        },
        "models": {
            "Action": {
                "classification": "spam | urgent | important | routine",
                "confidence": "float [0.0-1.0]",
                "needs_response": "boolean",
                "route_to": "string or null",
            },
        },
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "title": "Email Triage Environment API",
        "version": "1.0.0",
        "description": "OpenEnv-compliant email triage and classification environment",
        "docs_url": "/docs",
        "health_url": "/api/health",
    }


if __name__ == "__main__":
    import os
    
    port = int(os.getenv("PORT", 7860))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting Email Triage Environment API on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )
