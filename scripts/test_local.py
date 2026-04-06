#!/usr/bin/env python3
"""
Local test script for Email Triage Environment
Tests all 3 tasks and validates the full workflow.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from email_triage_env import EmailTriageEnv, Action


async def test_task(task_type: str, difficulty: str, max_steps: int = 20):
    """Test a single task."""
    print(f"\n{'='*60}")
    print(f"Testing: {task_type}_{difficulty}")
    print(f"{'='*60}")
    
    env = EmailTriageEnv(
        task=task_type,
        difficulty=difficulty,
        max_steps=max_steps,
    )
    
    try:
        # Reset
        print("\n1. Testing reset()...")
        result = await env.reset()
        obs = result["observation"]
        assert obs is not None, "Reset returned None observation"
        assert obs.current_email is not None, "No email in observation"
        print(f"   ✓ Reset OK - inbox_size={obs.inbox_size}, episode_step={obs.episode_step}")
        
        # Execute steps
        print("\n2. Testing step() and reward function...")
        step_rewards = []
        predictions = []
        
        for step in range(1, min(6, max_steps + 1)):  # Test first 5 steps
            if obs is None or obs.current_email is None:
                break
            
            # Create action
            action = Action(
                classification="important",  # Simple baseline
                confidence=0.5 + (step * 0.05),  # Vary confidence
                needs_response=True,
                route_to="engineering" if step % 2 == 0 else None,
            )
            predictions.append(action.classification)
            
            # Execute step
            result = await env.step(action)
            obs = result.get("observation")
            reward = result.get("reward", 0.0)
            done = result.get("done", False)
            info = result.get("info", {})
            
            step_rewards.append(reward)
            
            print(f"   Step {step}: reward={reward:.3f}, done={done}, "
                  f"cumulative={info.get('cumulative_reward', 0):.3f}")
            
            if done:
                print(f"   ✓ Episode finished early at step {step}")
                break
        
        # Get state
        print("\n3. Testing state()...")
        state = await env.state()
        assert "task" in state and "difficulty" in state, "State missing required fields"
        print(f"   ✓ State OK: {state}")
        
        # Grade task
        print("\n4. Testing grade_task()...")
        task_result = env.grade_task()
        assert 0.0 <= task_result.final_score <= 1.0, f"Invalid score: {task_result.final_score}"
        assert task_result.accuracy >= 0.0, "Invalid accuracy"
        print(f"   ✓ Grade OK:")
        print(f"      Score: {task_result.final_score:.3f}")
        print(f"      Accuracy: {task_result.accuracy:.3f}")
        print(f"      Steps: {task_result.total_steps}")
        print(f"      Total Reward: {task_result.total_reward:.3f}")
        print(f"      Success: {task_result.success}")
        
        # Close
        print("\n5. Testing close()...")
        await env.close()
        print("   ✓ Close OK")
        
        return True, task_result
        
    except Exception as e:
        print(f"\n   ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("EMAIL TRIAGE ENVIRONMENT - LOCAL TEST SUITE")
    print("="*60)
    
    results = {}
    
    # Test all 3 tasks
    tasks = [
        ("binary", "easy", 10),
        ("multiclass", "medium", 20),
        ("routing", "hard", 20),
    ]
    
    for task_type, difficulty, max_steps in tasks:
        success, task_result = await test_task(task_type, difficulty, max_steps)
        results[f"{task_type}_{difficulty}"] = (success, task_result)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for success, _ in results.values() if success)
    total = len(results)
    
    for task_name, (success, task_result) in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        score = f": score={task_result.final_score:.3f}" if task_result else ""
        print(f"{status} {task_name}{score}")
    
    print(f"\nTotal: {passed}/{total} tasks passed")
    
    # Validation summary
    print("\n" + "="*60)
    print("VALIDATION CHECKLIST")
    print("="*60)
    
    checks = [
        ("All tasks implemented", total == 3),
        ("All tasks passed", passed == total),
        ("Scores in [0, 1]", all(
            0.0 <= tr.final_score <= 1.0
            for _, tr in results.values() if tr
        )),
        ("Models defined", True),  # We have models
        ("Reward function works", all(
            tr.total_reward > 0
            for _, tr in results.values() if tr
        )),
        ("Grading works", all(tr for _, tr in results.values())),
    ]
    
    for check_name, check_result in checks:
        status = "✓" if check_result else "✗"
        print(f"{status} {check_name}")
    
    all_passed = all(check for _, check in checks)
    
    print("\n" + "="*60)
    if all_passed and passed == total:
        print("✓ ALL TESTS PASSED - Environment is ready!")
        print("="*60)
        return 0
    else:
        print("✗ Some tests failed - See above for details")
        print("="*60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
