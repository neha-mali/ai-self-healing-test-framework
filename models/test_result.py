# defines what a test result looks like

from dataclasses import dataclass


@dataclass
class TestResult:
    test_name: str
    url: str
    passed: bool
    actual_result: str
    screenshot_path: str
    is_healed: bool = False
    healed_selector: str = None
    bug_severity: str = None
    bug_reason: str = None

# result = TestResult(
#     test_name="Login test",
#     url="https://opensource-demo.orangehrmlive.com",
#     passed=True,
#     actual_result="DONE: dashboard loaded successfully",
#     screenshot_path="screenshots/step_4.png",
#     is_healed=True,
#     healed_selector="click [ref=e32] → click [ref=e45]"
# )