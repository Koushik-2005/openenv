"""
Pydantic models for Email Triage Environment.
Defines type-safe Observation, Action, and Reward schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal


class EmailMessage(BaseModel):
    """Represents a single email message."""
    id: str = Field(description="Unique email ID")
    sender: str = Field(description="Email sender address")
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Email body content")
    timestamp: str = Field(description="ISO 8601 timestamp")
    is_internal: bool = Field(description="Whether sender is internal to organization")
    has_attachment: bool = Field(description="Whether email has attachments")
    word_count: int = Field(description="Number of words in body")


class Observation(BaseModel):
    """
    Current environment observation.
    Represents the state of the inbox and pending actions.
    """
    current_email: EmailMessage = Field(description="Email to classify")
    inbox_size: int = Field(description="Total emails in inbox")
    processed_count: int = Field(description="Emails processed so far")
    episode_step: int = Field(description="Current step in episode")
    task_description: str = Field(description="Description of current task")


class Action(BaseModel):
    """
    Agent action: classify and optionally route the email.
    """
    classification: Literal["spam", "urgent", "important", "routine"] = Field(
        description="Email classification"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in classification (0.0-1.0)"
    )
    needs_response: bool = Field(
        description="Whether email needs response"
    )
    route_to: Optional[str] = Field(
        default=None,
        description="Routing destination (e.g., 'support', 'sales', 'engineering')"
    )


class Reward(BaseModel):
    """
    Reward signal after each action.
    """
    step_reward: float = Field(
        ge=0.0, le=1.0,
        description="Reward for this step"
    )
    classification_accuracy: float = Field(
        ge=0.0, le=1.0,
        description="Accuracy component of reward"
    )
    confidence_bonus: float = Field(
        ge=-0.1, le=0.1,
        description="Bonus/penalty for confidence calibration"
    )
    routing_bonus: float = Field(
        ge=-0.1, le=0.1,
        description="Bonus/penalty for routing correctness"
    )
    episode_step: int = Field(description="Step count")
    cumulative_reward: float = Field(
        ge=0.0,
        description="Total reward accumulated this episode"
    )


class TaskResult(BaseModel):
    """
    Result of task evaluation after episode completes.
    """
    task_name: str = Field(description="Name of the task")
    success: bool = Field(description="Whether task was successfully completed")
    final_score: float = Field(
        ge=0.0, le=1.0,
        description="Final score for the task (0.0-1.0)"
    )
    accuracy: float = Field(
        ge=0.0, le=1.0,
        description="Classification accuracy"
    )
    total_steps: int = Field(description="Total steps taken")
    total_reward: float = Field(description="Total cumulative reward")
    details: Optional[dict] = Field(
        default=None,
        description="Additional task-specific details"
    )
