"""
Email Triage Environment - Main OpenEnv implementation.
Simulates a realistic email triage task for AI agents.
"""
import asyncio
import json
from typing import Optional, Literal
from .models import Observation, Action, Reward, EmailMessage, TaskResult
from .simulator import EmailSimulator
from .reward_engine import RewardEngine, TaskGrader


class EmailTriageEnv:
    """
    OpenEnv-compliant Email Triage Environment.
    
    Task: Agent must classify and triage incoming emails.
    Observation space: Current email + inbox metadata
    Action space: Classification + confidence + routing
    Reward: Accuracy + confidence calibration + efficiency
    """

    def __init__(
        self,
        task: Literal["binary", "multiclass", "routing"] = "multiclass",
        difficulty: Literal["easy", "medium", "hard"] = "medium",
        max_steps: int = 20,
    ):
        self.task = task
        self.difficulty = difficulty
        self.max_steps = max_steps

        # Episode state
        self.emails = []
        self.current_step = 0
        self.done = False
        self.agent_actions = []
        self.rewards_list = []
        self.ground_truth = []
        self.reward_engine = RewardEngine(max_steps)

        # Task descriptions
        self.task_descriptions = {
            "binary": "Classify emails as spam or legitimate. Spam emails are malicious/unwanted. Legitimate emails require processing.",
            "multiclass": "Classify emails into 4 categories: spam (unwanted), urgent (needs immediate action), important (needs response), routine (informational). Higher priority emails should be processed first.",
            "routing": "Classify emails AND route them to the correct department (support, sales, engineering, hr). Misrouting is costly.",
        }

    def _normalize_ground_truth(self, label: str) -> str:
        """Map simulator labels to the action-space labels used by this environment."""
        if self.task == "binary" and label == "legitimate":
            return "routine"
        return label

    async def reset(self) -> dict:
        """
        Reset environment and start new episode.
        Returns initial observation.
        """
        self.current_step = 0
        self.done = False
        self.agent_actions = []
        self.rewards_list = []
        self.ground_truth = []
        self.reward_engine.reset()

        # Generate email batch for this episode
        inbox_size = self.max_steps
        self.emails = EmailSimulator.generate_batch(
            size=inbox_size,
            task_type=self.task,
            difficulty=self.difficulty,
        )

        initial_email, ground_truth = self.emails[0]
        self.ground_truth.append(self._normalize_ground_truth(ground_truth))

        observation = Observation(
            current_email=initial_email,
            inbox_size=inbox_size,
            processed_count=0,
            episode_step=0,
            task_description=self.task_descriptions[self.task],
        )

        return {
            "observation": observation,
            "done": False,
            "info": {},
        }

    async def step(self, action: Action) -> dict:
        """
        Execute one step: agent classifies an email.
        Returns next observation, reward, done, info.
        """
        if self.done:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")

        self.current_step += 1

        # Get ground truth for current email
        _, true_classification = self.emails[self.current_step - 1]
        true_classification = self._normalize_ground_truth(true_classification)

        # Compute reward for this action
        reward = self.reward_engine.compute_step_reward(
            predicted_classification=action.classification,
            true_classification=true_classification,
            confidence=action.confidence,
            predicted_routing=action.route_to,
            true_routing=None,  # For now, routing is optional
            is_final_step=(self.current_step >= self.max_steps),
        )

        self.agent_actions.append(action)
        self.rewards_list.append(reward.step_reward)

        # Check if episode is done
        self.done = self.current_step >= self.max_steps

        # Prepare next observation
        if self.done:
            next_email = None
        else:
            next_email, next_ground_truth = self.emails[self.current_step]
            self.ground_truth.append(self._normalize_ground_truth(next_ground_truth))

        observation = Observation(
            current_email=next_email,
            inbox_size=len(self.emails),
            processed_count=self.current_step,
            episode_step=self.current_step,
            task_description=self.task_descriptions[self.task],
        ) if not self.done else None

        info = {
            "classification_accuracy": reward.classification_accuracy,
            "confidence_bonus": reward.confidence_bonus,
            "routing_bonus": reward.routing_bonus,
            "cumulative_reward": reward.cumulative_reward,
        }

        return {
            "observation": observation,
            "reward": reward.step_reward,
            "done": self.done,
            "info": info,
        }

    async def state(self) -> dict:
        """Return current environment state for debugging."""
        return {
            "task": self.task,
            "difficulty": self.difficulty,
            "current_step": self.current_step,
            "max_steps": self.max_steps,
            "done": self.done,
            "cumulative_reward": self.reward_engine.cumulative_reward,
            "accuracy_so_far": self._compute_accuracy() if self.current_step > 0 else 0.0,
        }

    def _compute_accuracy(self) -> float:
        """Compute classification accuracy so far."""
        if len(self.agent_actions) == 0:
            return 0.0
        correct = sum(
            1 for a, gt in zip(self.agent_actions, self.ground_truth)
            if a.classification == gt
        )
        return correct / len(self.agent_actions)

    def grade_task(self) -> TaskResult:
        """
        Grade the completed task.
        Returns TaskResult with score (0.0-1.0) and success status.
        """
        predictions = [a.classification for a in self.agent_actions]
        accuracy = self._compute_accuracy()

        success, score = TaskGrader.grade_task(
            task_name=self.task,
            predictions=predictions,
            ground_truth=self.ground_truth,
            all_rewards=self.rewards_list,
            total_steps=self.current_step,
            difficulty=self.difficulty,
        )

        return TaskResult(
            task_name=f"{self.task}_{self.difficulty}",
            success=success,
            final_score=score,
            accuracy=accuracy,
            total_steps=self.current_step,
            total_reward=sum(self.rewards_list),
            details={
                "processed_emails": len(predictions),
                "true_classifications": self.ground_truth,
                "agent_classifications": predictions,
            },
        )

    async def close(self):
        """Cleanup and close environment."""
        pass


class EmailTriageEnvV1(EmailTriageEnv):
    """Versioned environment class for compatibility."""
    pass
