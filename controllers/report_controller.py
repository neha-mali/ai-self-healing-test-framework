# generates an Allure-compatible report from test results

import os
import json
import uuid
import time
import subprocess
from models.test_result import TestResult


ALLURE_RESULTS_DIR = "allure-results"


def generate_allure_report(results: list[TestResult]):
    # make sure the results folder exists
    os.makedirs(ALLURE_RESULTS_DIR, exist_ok=True)

    for result in results:
        write_allure_result(result)

    print(f"\n📊 Wrote {len(results)} result(s) to {ALLURE_RESULTS_DIR}/")

    # ask the allure CLI to generate and open the html report
    print("Generating Allure report...")
    subprocess.run([
        "allure", "generate", ALLURE_RESULTS_DIR,
        "--clean", "-o", "allure-report"
    ])

    print("Opening report in browser...")
    subprocess.run(["allure", "open", "allure-report"])


def write_allure_result(result: TestResult):
    # allure expects one json file per test, in a specific schema
    test_uuid = str(uuid.uuid4())
    now_ms = int(time.time() * 1000)

    status = "passed" if result.passed else "failed"

    allure_test = {
        "uuid": test_uuid,
        "name": result.test_name,
        "status": status,
        "statusDetails": {
            "message": result.actual_result
        },
        "stage": "finished",
        "start": now_ms,
        "stop": now_ms,
        "labels": [
            {"name": "suite", "value": "AI Self Healing Test Framework"}
        ],
        "parameters": [
            {"name": "url", "value": result.url}
        ]
    }

    # add a label if this test had a selector healed
    if result.is_healed:
        allure_test["labels"].append(
            {"name": "tag", "value": "self-healed"}
        )
        allure_test["statusDetails"]["message"] += (
            f"\n\n🔧 Selector healed: {result.healed_selector}"
        )

    file_path = os.path.join(
        ALLURE_RESULTS_DIR, f"{test_uuid}-result.json"
    )

    with open(file_path, "w") as f:
        json.dump(allure_test, f, indent=2)

    print(f"   Wrote: {result.test_name} → {status}")


if __name__ == "__main__":
    # test with fake results, no need to run real browser
    fake_results = [
        TestResult(
            test_name="OrangeHRM Login",
            url="https://opensource-demo.orangehrmlive.com",
            passed=True,
            actual_result="DONE: dashboard loaded successfully",
            screenshot_path=""
        ),
        TestResult(
            test_name="OrangeHRM Login with wrong password",
            url="https://opensource-demo.orangehrmlive.com",
            passed=True,
            actual_result="DONE: error message correctly shown",
            screenshot_path=""
        ),
        TestResult(
            test_name="OrangeHRM Healed Selector Example",
            url="https://opensource-demo.orangehrmlive.com",
            passed=True,
            actual_result="DONE: dashboard loaded after healing",
            screenshot_path="",
            is_healed=True,
            healed_selector="click [ref=e32] → click [ref=e45]"
        )
    ]

    generate_allure_report(fake_results)














# Takes: list of TestResult objects
#         ↓
# Formats each one properly
#         ↓
# Generates an Allure-compatible report
#         ↓
# Opens the report in your browser automatically


# Step 1: Your code writes JSON result files
#         into an "allure-results" folder
#         (one JSON file per test)
#
# Step 2: A separate command-line tool called
#         "allure" reads that folder and
#         generates the final HTML report
#
# Step 3: "allure serve" or "allure generate"
#         opens it in your browser