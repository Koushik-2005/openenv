"""
Email Triage Environment - OpenEnv Implementation
"""
from .models import Observation, Action, Reward, EmailMessage, TaskResult
from .environment import EmailTriageEnv, EmailTriageEnvV1
from .simulator import EmailSimulator
from .reward_engine import RewardEngine, TaskGrader

__version__ = "1.0.0"
__all__ = [
    "EmailTriageEnv",
    "EmailTriageEnvV1",
    "Observation",
    "Action",
    "Reward",
    "EmailMessage",
    "TaskResult",
    "EmailSimulator",
    "RewardEngine",
    "TaskGrader",
]
