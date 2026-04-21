#!/usr/bin/env python3
"""Test script to validate agent deep work capabilities.

This script tests if agents can now perform longer investigation sessions
with the increased iteration limits.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mindflow_backend.agents.specialists.runtime_policy import get_agent_runtime_policy


def test_iteration_limits():
    """Verify that iteration limits have been increased."""
    print("🔍 Testing Iteration Limits\n")

    agents_to_test = [
        ("analyst", 25),
        ("analyst:deep_iteration", 15),
        ("coder", 30),
        ("researcher", 20),
        ("orchestrator", 50),
    ]

    results = []
    for agent_id, expected_limit in agents_to_test:
        try:
            policy = get_agent_runtime_policy(agent_id=agent_id)
            actual_limit = policy.max_iterations
            status = "✅" if actual_limit >= expected_limit else "❌"
            results.append({
                "agent": agent_id,
                "expected": expected_limit,
                "actual": actual_limit,
                "status": status
            })
            print(f"{status} {agent_id:30s} Expected: {expected_limit:3d}  Actual: {actual_limit:3d}")
        except Exception as e:
            print(f"❌ {agent_id:30s} Error: {e}")
            results.append({"agent": agent_id, "status": "❌", "error": str(e)})

    print(f"\n📊 Results: {sum(1 for r in results if r['status'] == '✅')}/{len(results)} passed")
    return all(r["status"] == "✅" for r in results)


def test_deep_work_module():
    """Verify deep work module is importable and functional."""
    print("\n🔍 Testing Deep Work Module\n")

    try:
        from mindflow_backend.orchestrator.deep_work import (
            build_continuation_context,
            should_continue_investigation,
        )

        # Test continuation detection
        test_cases = [
            ("I need to explore further", True),
            ("Let me investigate this more", True),
            ("Preciso investigar mais", True),
            ("Analysis complete", False),
            ("Done", False),
        ]

        passed = 0
        for text, expected in test_cases:
            should_continue, reason = should_continue_investigation(text, current_depth=1)
            if should_continue == expected:
                print(f"✅ '{text[:30]}...' → {should_continue}")
                passed += 1
            else:
                print(f"❌ '{text[:30]}...' → {should_continue} (expected {expected})")

        # Test context building
        context = build_continuation_context(
            "Previous analysis found X",
            ["Turn 1: Found Y", "Turn 2: Discovered Z"],
            current_depth=2
        )

        if "CONTINUATION TURN 3" in context and "Previous Investigation" in context:
            print("✅ Context building works")
            passed += 1
        else:
            print("❌ Context building failed")

        print(f"\n📊 Results: {passed}/{len(test_cases) + 1} passed")
        return passed == len(test_cases) + 1

    except Exception as e:
        print(f"❌ Error importing deep_work module: {e}")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("🧪 MindFlow Agent Deep Work Validation")
    print("=" * 70)

    test1 = test_iteration_limits()
    test2 = test_deep_work_module()

    print("\n" + "=" * 70)
    if test1 and test2:
        print("✅ ALL TESTS PASSED - Agents ready for deep work!")
    else:
        print("❌ SOME TESTS FAILED - Review configuration")
    print("=" * 70)

    sys.exit(0 if (test1 and test2) else 1)
