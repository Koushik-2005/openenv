#!/usr/bin/env python3
"""
Pre-submission validation script.
Checks all requirements for OpenEnv Round 1 submission.
"""

import sys
import os
import json
from pathlib import Path

def check(condition: bool, message: str) -> bool:
    """Check a condition and print result."""
    status = "✓" if condition else "✗"
    print(f"{status} {message}")
    return condition


def main():
    print("\n" + "="*60)
    print("OPENENV ROUND 1 PRE-SUBMISSION VALIDATION")
    print("="*60)
    
    all_passed = True
    
    # 1. Check file structure
    print("\n[1] FILE STRUCTURE")
    files_required = [
        "openenv.yaml",
        "inference.py",
        "Dockerfile",
        "requirements.txt",
        "README.md",
        "email_triage_env/__init__.py",
        "email_triage_env/models.py",
        "email_triage_env/environment.py",
        "email_triage_env/simulator.py",
        "email_triage_env/reward_engine.py",
    ]
    
    for file_path in files_required:
        exists = Path(file_path).exists()
        all_passed &= check(exists, f"File exists: {file_path}")
    
    # 2. Check openenv.yaml
    print("\n[2] OPENENV.YAML VALIDATION")
    try:
        import yaml
        with open("openenv.yaml") as f:
            spec = yaml.safe_load(f)
        
        required_fields = ["name", "version", "description", "env", "observation", "action", "reward", "tasks"]
        for field in required_fields:
            exists = field in spec
            all_passed &= check(exists, f"Field '{field}' in openenv.yaml")
        
        # Check tasks
        tasks = spec.get("tasks", [])
        all_passed &= check(len(tasks) >= 3, f"At least 3 tasks defined (found {len(tasks)})")
        
        for i, task in enumerate(tasks):
            required_task_fields = ["name", "description", "difficulty"]
            for field in required_task_fields:
                exists = field in task
                all_passed &= check(exists, f"Task {i} field '{field}'")
    
    except Exception as e:
        all_passed &= check(False, f"openenv.yaml valid YAML: {e}")
    
    # 3. Check Python imports
    print("\n[3] PYTHON IMPORTS")
    try:
        from email_triage_env import EmailTriageEnv, Observation, Action, Reward
        check(True, "Can import environment classes")
    except Exception as e:
        all_passed &= check(False, f"Import environment: {e}")
    
    try:
        from pydantic import BaseModel
        check(True, "Pydantic models available")
    except:
        all_passed &= check(False, "Pydantic not installed")
    
    # 4. Check inference.py
    print("\n[4] INFERENCE SCRIPT")
    try:
        with open("inference.py") as f:
            content = f.read()
        
        checks = [
            ("[START]" in content, "Contains [START] logging"),
            ("[STEP]" in content, "Contains [STEP] logging"),
            ("[END]" in content, "Contains [END] logging"),
            ("OpenAI" in content, "Uses OpenAI client"),
            ("asyncio" in content, "Is async-compatible"),
            ("MODEL_NAME" in content, "Uses MODEL_NAME env var"),
            ("API_BASE_URL" in content or "api_base" in content.lower(), "Uses API_BASE_URL"),
        ]
        
        for check_cond, check_msg in checks:
            all_passed &= check(check_cond, check_msg)
    
    except Exception as e:
        all_passed &= check(False, f"Read inference.py: {e}")
    
    # 5. Check Dockerfile
    print("\n[5] DOCKERFILE VALIDATION")
    try:
        with open("Dockerfile") as f:
            content = f.read()
        
        checks = [
            ("FROM" in content, "Contains FROM clause"),
            ("python" in content.lower(), "Based on Python image"),
            ("requirements.txt" in content, "Installs requirements"),
            ("EXPOSE" in content or "7860" in content, "Exposes port"),
            ("CMD" in content or "ENTRYPOINT" in content, "Has entrypoint"),
        ]
        
        for check_cond, check_msg in checks:
            all_passed &= check(check_cond, check_msg)
    
    except Exception as e:
        all_passed &= check(False, f"Read Dockerfile: {e}")
    
    # 6. Check requirements.txt
    print("\n[6] REQUIREMENTS VALIDATION")
    try:
        with open("requirements.txt") as f:
            reqs = f.read()
        
        required_packages = [
            "pydantic",
            "openai",
            "openenv",
        ]
        
        for pkg in required_packages:
            present = pkg.lower() in reqs.lower()
            all_passed &= check(present, f"Package '{pkg}' in requirements.txt")
    
    except Exception as e:
        all_passed &= check(False, f"Read requirements.txt: {e}")
    
    # 7. Check README
    print("\n[7] README VALIDATION")
    try:
        with open("README.md") as f:
            readme = f.read()
        
        required_sections = [
            ("Environment Overview", ["overview", "description"]),
            ("Tasks", ["task", "mission"]),
            ("Action Space", ["action"]),
            ("Observation Space", ["observation"]),
            ("Setup Instructions", ["setup", "install", "quick start"]),
            ("Baseline Performance", ["baseline", "score", "performance"]),
        ]
        
        for section, keywords in required_sections:
            found = any(kw in readme.lower() for kw in keywords)
            all_passed &= check(found, f"README has {section}")
    
    except Exception as e:
        all_passed &= check(False, f"Read README.md: {e}")
    
    # 8. Environment Functionality
    print("\n[8] ENVIRONMENT FUNCTIONALITY TEST")
    try:
        import asyncio
        from email_triage_env import EmailTriageEnv, Action
        
        async def test():
            env = EmailTriageEnv(task="multiclass", difficulty="easy", max_steps=5)
            
            # Test reset
            result = await env.reset()
            assert "observation" in result
            
            # Test step
            action = Action(
                classification="important",
                confidence=0.5,
                needs_response=True
            )
            result = await env.step(action)
            assert "reward" in result and "done" in result
            
            # Test state
            state = await env.state()
            assert isinstance(state, dict)
            
            # Test close
            await env.close()
            
            return True
        
        try:
            success = asyncio.run(test())
            all_passed &= check(success, "Environment API functions correctly")
        except Exception as e:
            all_passed &= check(False, f"Environment test: {e}")
    
    except Exception as e:
        all_passed &= check(False, f"Setup for environment test: {e}")
    
    # 9. Check for 3 tasks with graders
    print("\n[9] TASKS & GRADERS")
    try:
        from email_triage_env import EmailTriageEnv
        
        task_configs = [
            ("binary", "easy"),
            ("multiclass", "medium"),
            ("routing", "hard"),
        ]
        
        for task_type, difficulty in task_configs:
            try:
                env = EmailTriageEnv(task=task_type, difficulty=difficulty)
                # If we can create it, it exists
                all_passed &= check(True, f"Task {task_type}_{difficulty} defined")
            except Exception:
                all_passed &= check(False, f"Task {task_type}_{difficulty} defined")
    
    except Exception as e:
        all_passed &= check(False, f"Tasks check: {e}")
    
    # Final summary
    print("\n" + "="*60)
    if all_passed:
        print("✓ ALL CHECKS PASSED - Ready for submission!")
        print("="*60)
        print("\nNext steps:")
        print("1. Set up environment variables (see .env.example)")
        print("2. Run: python inference.py")
        print("3. Deploy to Hugging Face Spaces")
        print("4. Submit at: https://www.scaler.com/openenv")
        return 0
    else:
        print("✗ Some checks failed - See above for details")
        print("="*60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
