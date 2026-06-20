# defines what a test case looks like

from dataclasses import dataclass


@dataclass
class TestCase:
    name: str
    url: str
    steps: str
    expected_result: str


# Why it exists: Without this, every test would just be a loose dictionary — easy to misspell a key
# ("nmae" instead of "name") and get a silent bug. With @dataclass, every test case is guaranteed to have
# these exact fields, and your editor will warn you if you forget one

# test = TestCase(
#     name="Login test",
#     url="https://opensource-demo.orangehrmlive.com",
#     steps="Login with Admin and admin123",
#     expected_result="Dashboard loads"
# )