"""
Reward function for email triage environment.
Provides meaningful partial progress signals and penalizes bad behavior.
"""
from typing import Optional
from .models import Reward


class RewardEngine:
    """
    Computes reward signals with partial progress feedback.
    
    Reward components:
    - Classification accuracy: 0.5 base (agent must classify correctly)
    - Confidence calibration: ±0.2 bonus/penalty (well-calibrated confidence is valuable)
    - Routing bonus: ±0.2 bonus/penalty (correct routing of escalations)
    - Early termination penalty: -0.1 (don't give up)
    """

    def __init__(self, max_steps: int = 20):
        self.max_steps = max_steps
        self.step_count = 0
        self.cumulative_reward = 0.0

    def reset(self):
        """Reset state for new episode."""
        self.step_count = 0
        self.cumulative_reward = 0.0

    def compute_step_reward(
        self,
        predicted_classification: str,
        true_classification: str,
        confidence: float,
        predicted_routing: Optional[str],
        true_routing: Optional[str],
        is_final_step: bool,
    ) -> Reward:
        """
        Compute reward for a single step.
        
        Args:
            predicted_classification: Agent's classification
            true_classification: Ground truth
            confidence: Confidence score (0.0-1.0)
            predicted_routing: Agent's routing prediction (if any)
            true_routing: Ground truth routing (if any)
            is_final_step: Whether this is the last step
            
        Returns:
            Reward object
        """
        self.step_count += 1

        # Classification accuracy component (0.0-0.5)
        classification_correct = predicted_classification == true_classification
        classification_accuracy = 0.5 if classification_correct else 0.0

        # Confidence calibration component (±0.2)
        # High confidence on correct predictions: +0.1
        # Low confidence on correct predictions: +0.05
        # High confidence on wrong predictions: -0.1
        # Low confidence on wrong predictions: 0.0
        if classification_correct:
            confidence_bonus = 0.1 if confidence > 0.7 else 0.05
            confidence_bonus = min(0.2, confidence_bonus)
        else:
            confidence_bonus = -0.1 if confidence > 0.7 else 0.0

        # Routing bonus component (±0.2)
        routing_bonus = 0.0
        if predicted_routing is not None and true_routing is not None:
            if predicted_routing == true_routing:
                routing_bonus = 0.1
            else:
                routing_bonus = -0.05

        # Step reward (sum of components, clamped to [0, 1])
        step_reward = classification_accuracy + confidence_bonus + routing_bonus
        step_reward = max(0.0, min(1.0, step_reward))

        # Update cumulative
        self.cumulative_reward += step_reward

        reward_obj = Reward(
            step_reward=step_reward,
            classification_accuracy=classification_accuracy,
            confidence_bonus=confidence_bonus,
            routing_bonus=routing_bonus,
            episode_step=self.step_count,
            cumulative_reward=self.cumulative_reward,
        )

        return reward_obj

    def compute_episode_score(
        self,
        total_accuracy: float,
        total_steps: int,
        task_type: str,
    ) -> float:
        """
        Compute final episode score (0.0-1.0).
        
        Score incorporates:
        - Accuracy: How many emails classified correctly
        - Efficiency: Fewer steps is better (but not at the cost of accuracy)
        - Task difficulty multiplier
        """
        if total_steps == 0:
            return 0.0

        # Accuracy component (70%)
        accuracy_score = total_accuracy * 0.7

        # Efficiency component (30%)
        # Optimal is close to max_steps but not necessarily completing all
        efficiency = max(0.0, 1.0 - (total_steps / (self.max_steps * 1.5)))
        efficiency_score = efficiency * 0.3

        # Combined score
        final_score = accuracy_score + efficiency_score
        final_score = max(0.0, min(1.0, final_score))

        return final_score


class TaskGrader:
    """
    Grades agent performance on specific task.
    """

    @staticmethod
    def grade_task(
        task_name: str,
        predictions: list,
        ground_truth: list,
        all_rewards: list,
        total_steps: int,
        difficulty: str,
    ) -> tuple[bool, float]:
        """
        Grade task completion.
        
        Returns: (success: bool, score: float in [0, 1])
        """
        if len(predictions) == 0:
            return False, 0.0

        # Accuracy
        correct = sum(1 for p, gt in zip(predictions, ground_truth) if p == gt)
        accuracy = correct / len(predictions)

        # Total accumulated reward
        total_reward = sum(all_rewards) if all_rewards else 0.0
        max_possible_reward = len(predictions) * 1.0  # Max 1.0 per step

        # Difficulty thresholds
        thresholds = {
            "easy": 0.85,      # Must achieve 85% accuracy on easy task
            "medium": 0.70,    # Must achieve 70% on medium
            "hard": 0.55,      # Must achieve 55% on hard
        }

        required_accuracy = thresholds.get(difficulty, 0.70)

        # Success: achieved required accuracy
        success = accuracy >= required_accuracy

        # Final score: weighted average of accuracy and efficiency
        reward_efficiency = total_reward / max_possible_reward if max_possible_reward > 0 else 0.0
        final_score = 0.7 * accuracy + 0.3 * reward_efficiency

        return success, min(1.0, final_score)
