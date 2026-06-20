# handles self healing when elements are not found

import re
from core.mcp_client import get_claude_client


def heal_action(failed_action, snapshot, error_message):
    """
    Takes a failed action and finds the correct element.

    failed_action → what we tried to do
    snapshot      → current page structure
    error_message → what went wrong

    Returns healed action or None if healing failed
    """
    client = get_claude_client()

    print(f"\n🔧 Self healing triggered!")
    print(f"Failed action: {failed_action}")
    print(f"Error: {error_message}")

    # ask claude to find the correct element
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=200,
        messages=[
            {
                "role": "user",
                "content": f"""
                I tried to perform this action but it failed:
                Action: {failed_action}
                Error: {error_message}
                
                Current page structure:
                {snapshot}
                
                The element is missing. Find the best matching 
                element from the page structure above.
                
                 Rules:
                1. Look for similar elements by type and purpose
                2. If action was "click Login" find a button to click
                3. If action was "fill Username" find a textbox to fill
                4. ONLY reply with one line — nothing else
                
                Reply with EXACTLY one of:
                HEALED: click [ref=eXX]
                HEALED: fill [ref=eXX] with [value]
                CANNOT_HEAL: reason
                """
            }
        ]
    )

    heal_decision = response.content[0].text
    print(f"Heal decision: {heal_decision}")

    # check if healing succeeded
    if "HEALED:" in heal_decision:
        healed_action = heal_decision.split("HEALED:")[1].strip()
        print(f"✅ Healed! New action: {healed_action}")
        return healed_action

    print(f"❌ Cannot heal: {heal_decision}")
    return None


def log_healing(original_action, healed_action):
    """
    Logs what was healed for the report.
    """
    print(f"\n📝 Healing log:")
    print(f"   Original: {original_action}")
    print(f"   Healed:   {healed_action}")

    return {
        "original": original_action,
        "healed": healed_action,
        "status": "healed"
    }


if __name__ == "__main__":
    # test healing with a fake scenario
    fake_snapshot = """
    - button "Sign In" [ref=e45] [cursor=pointer]
    - textbox "Email" [ref=e23]
    - textbox "Password" [ref=e28]
    """

    result = heal_action(
        failed_action="click [ref=e32]",
        snapshot=fake_snapshot,
        error_message='Element ref=e32 not found — was trying to click the Login/Sign In button'
    )

    if result:
        log_healing("click [ref=e32]", result)








"""

MCP action fails → element not found
        ↓
heal_controller catches the error
        ↓
Takes page snapshot
        ↓
Asks Claude:
"element X not found
 look at snapshot and find it"
        ↓
Claude finds new ref
        ↓
Retries with new ref
        ↓
Test passes ✅
        ↓
Logs old selector → new selector

"""