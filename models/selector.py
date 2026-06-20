# defines selector data structure for self healing

from dataclasses import dataclass


@dataclass
class Selector:
    element_name: str
    old_selector: str
    new_selector: str = None
    is_healed: bool = False
    heal_attempts: int = 0

# Why it exists: This is purely for reporting/visibility — so when the Allure report gets built, you can show a
# "selector healing history" section: "Login button: ref=e32 → ref=e45, healed automatically." Like test_result.py,
# this is defined but not yet wired into heal_controller.py's log_healing() function, which currently just returns
# a plain dict instead of a Selector object.

# sel = Selector(
#     element_name="Login button",
#     old_selector="ref=e32",
#     new_selector="ref=e45",
#     is_healed=True,
#     heal_attempts=1
# )