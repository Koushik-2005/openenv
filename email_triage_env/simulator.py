"""
Email simulator: generates realistic email data for different tasks.
"""
import random
import string
from datetime import datetime, timedelta
from typing import List, Literal
from .models import EmailMessage


class EmailSimulator:
    """Generates synthetic but realistic email messages."""

    # Email templates and datasets
    URGENT_SUBJECTS = [
        "CRITICAL: System Down",
        "URGENT: Security Breach Detected",
        "IMMEDIATE: Customer Escalation",
        "VP Request: Quarterly Review Due TODAY",
        "URGENT: Payment Issue - Client A",
        "CRITICAL BUG: Production Failure",
    ]

    IMPORTANT_SUBJECTS = [
        "Quarterly Planning Meeting",
        "Project Kickoff: New Initiative",
        "Board Meeting Minutes",
        "Department Strategy Discussion",
        "Client Proposal Review",
        "Team Lead Update",
    ]

    ROUTINE_SUBJECTS = [
        "Team Standup Tomorrow",
        "Lunch & Learn Next Week",
        "Office Supplies Refill",
        "Schedule Change Notification",
        "Wiki Update Available",
        "Monthly Newsletter",
    ]

    SPAM_SUBJECTS = [
        "WIN FREE MONEY NOW!!!",
        "Click here for limited offer",
        "Congratulations! You've won!",
        "Free courses for you",
        "Reduce costs by 90%",
        "Hot dating singles nearby",
        "Work from home $5000/week",
        "Final Notice: Act Now!",
    ]

    URGENT_BODIES = [
        "The production database went down 5 minutes ago. All customer-facing services are offline. Please respond immediately with recovery plan.",
        "We've detected unusual login attempts from unfamiliar IPs. Security team needs access to audit logs urgently.",
        "Customer ABC Corp reports data loss. They are considering legal action. Executive bridge call in 15 minutes.",
        "Q3 results presentation is today at 2 PM. Need final numbers from all departments ASAP.",
    ]

    IMPORTANT_BODIES = [
        "We need to discuss the roadmap priorities for Q4. Engineering and product alignment is critical.",
        "Please review the attached proposal. This represents a significant opportunity for the company.",
        "Team: Please block 2 hours next week for strategic planning session.",
        "The new API design has been approved. Implementation plan attached.",
    ]

    ROUTINE_BODIES = [
        "Just a reminder about our daily 10 AM standup. See you there!",
        "The company is sponsoring a lunch and learn session about project management tools.",
        "Our office supplies are running low. Please submit requests by end of week.",
        "FYI: Schedule has changed slightly. New times attached.",
    ]

    SPAM_BODIES = [
        "Limited time offer! Buy now and get 90% discount on everything. Click here.",
        "You have been selected as a winner! Claim prize immediately.",
        "Become a millionaire working from home. No experience needed. Click here.",
        "Dear customer, your account needs verification. Click link.",
    ]

    INTERNAL_DOMAINS = ["@company.com", "@internal.company.com", "@myorg.net"]
    EXTERNAL_DOMAINS = ["@gmail.com", "@yahoo.com", "@outlook.com", "@client.com", "@vendor.io"]

    @staticmethod
    def generate_email(
        task_type: Literal["binary", "multiclass", "routing"],
        difficulty: Literal["easy", "medium", "hard"],
        true_classification: str = None,
    ) -> tuple[EmailMessage, str]:
        """
        Generate a synthetic email.
        
        Returns: (EmailMessage, true_classification)
        """
        # For easy mode, make classification obvious
        # For medium mode, add ambiguity
        # For hard mode, create challenging edge cases

        if true_classification is None:
            if difficulty == "easy":
                # Easy: 80% spam, 20% ham - obvious cases
                true_classification = random.choices(
                    ["spam", "legitimate"],
                    weights=[0.8, 0.2],
                )[0]
            elif difficulty == "medium":
                # Medium: balanced distribution with ambiguous cases
                true_classification = random.choice(["spam", "urgent", "important", "routine"])
            else:
                # Hard: tricky cases, imbalanced, edge cases
                true_classification = random.choices(
                    ["spam", "urgent", "important", "routine"],
                    weights=[0.1, 0.2, 0.3, 0.4],  # Hard to distinguish important vs routine
                )[0]

        email_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        timestamp = (datetime.now() - timedelta(seconds=random.randint(0, 3600))).isoformat()

        # Generate realistic content based on classification
        if true_classification == "spam":
            subject = random.choice(EmailSimulator.SPAM_SUBJECTS)
            body = random.choice(EmailSimulator.SPAM_BODIES)
            sender = f"spammer{random.randint(1, 1000)}@{random.choice(['fake.com', 'spam.net', 'pharma.io'])}"
            is_internal = False
            has_attachment = random.choice([True, False])
            word_count = len(body.split())

            # For medium/hard, add ambiguity by making some spam look legitimate
            if difficulty in ["medium", "hard"] and random.random() < 0.3:
                subject = random.choice(EmailSimulator.ROUTINE_SUBJECTS)
                body = "Please click here for important updates: " + body
                sender = random.choice([s.replace("@", "@spam-") for s in EmailSimulator.EXTERNAL_DOMAINS])[:-1]

        elif true_classification == "urgent":
            subject = random.choice(EmailSimulator.URGENT_SUBJECTS)
            body = random.choice(EmailSimulator.URGENT_BODIES)
            sender = f"vp{random.randint(1, 10)}@company.com"
            is_internal = True
            has_attachment = random.choice([True, False])
            word_count = len(body.split())

        elif true_classification == "important":
            subject = random.choice(EmailSimulator.IMPORTANT_SUBJECTS)
            body = random.choice(EmailSimulator.IMPORTANT_BODIES)
            sender = random.choice([f"lead{i}@company.com" for i in range(1, 10)])
            is_internal = random.choice([True, False])
            has_attachment = random.choice([True, False])
            word_count = len(body.split())

            # For hard mode, make some important emails look routine
            if difficulty == "hard" and random.random() < 0.2:
                subject = random.choice(EmailSimulator.ROUTINE_SUBJECTS)

        else:  # routine
            subject = random.choice(EmailSimulator.ROUTINE_SUBJECTS)
            body = random.choice(EmailSimulator.ROUTINE_BODIES)
            sender = random.choice([f"admin@company.com", f"hr@company.com", f"ops@company.com"])
            is_internal = True
            has_attachment = False
            word_count = len(body.split())

        email = EmailMessage(
            id=email_id,
            sender=sender,
            subject=subject,
            body=body,
            timestamp=timestamp,
            is_internal=is_internal,
            has_attachment=has_attachment,
            word_count=word_count,
        )

        return email, true_classification

    @staticmethod
    def generate_batch(
        size: int,
        task_type: Literal["binary", "multiclass", "routing"] = "multiclass",
        difficulty: Literal["easy", "medium", "hard"] = "medium",
    ) -> List[tuple[EmailMessage, str]]:
        """Generate a batch of emails with their true classifications."""
        return [
            EmailSimulator.generate_email(task_type, difficulty)
            for _ in range(size)
        ]
