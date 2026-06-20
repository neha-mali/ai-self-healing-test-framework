# orchestrates running multiple test cases and collecting results

import asyncio
from models.test_case import TestCase
from models.test_result import TestResult
from core.claude_agent import run_mcp_agent
from controllers.report_controller import generate_allure_report

async def run_test_session(test_cases: list[TestCase]) -> list[TestResult]:
    results = []

    for case in test_cases:
        print(f"\n{'='*50}")
        print(f"Running test case: {case.name}")
        print(f"{'='*50}")

        # run_mcp_agent returns a plain dict right now:
        # {"passed": bool, "reason": str, "steps": int}
        outcome = await run_mcp_agent(case.url, case.steps)

        # wrap it into our proper TestResult model
        result = TestResult(
            test_name=case.name,
            url=case.url,
            passed=outcome["passed"],
            actual_result=outcome["reason"],
            screenshot_path=""  # we'll wire this up later
        )

        results.append(result)

    return results

if __name__ == "__main__":
    test_cases = [
        TestCase(
            name="OrangeHRM Login",
            url="https://opensource-demo.orangehrmlive.com",
            steps="Login with username Admin and password admin123 and verify dashboard loads",
            expected_result="Dashboard loads with navigation menu visible"
        ),
        TestCase(
            name="OrangeHRM Login with wrong password",
            url="https://opensource-demo.orangehrmlive.com",
            steps="Login with username Admin and password wrongpass123 and verify an error message appears",
            expected_result="Login fails with an error message, page stays on login screen"
        )
    ]

    results = asyncio.run(run_test_session(test_cases))

    print(f"\n\n{'='*50}")
    print("SESSION SUMMARY")
    print(f"{'='*50}")
    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        print(f"{status} — {r.test_name}")
    # generate and open the allure report with real results
    generate_allure_report(results)