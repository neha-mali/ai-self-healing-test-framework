# connects to Playwright MCP server and manages Claude conversation

# aysnc allows waiting without blocking
import asyncio
from dotenv import load_dotenv
import re
from controllers.heal_controller import heal_action, log_healing

# client session manages our connection to MCP server
# StdioServerParameters tells python how to start MCP server
from mcp import ClientSession, StdioServerParameters

# stdio_client connects to MCP server, python talks to MCP through terminal pipes
from mcp.client.stdio import stdio_client
from core.mcp_client import get_claude_client

# Actually loads the .env file into memory so os.getenv() calls can find the API key
load_dotenv()


async def run_mcp_agent(url, task):

    # claude connection
    client = get_claude_client()

    # Empty list that will store the full chat history with Claude — needed because Claude has no memory
    # between API calls.
    conversation = []

    # loop should run forever
    max_steps = 10
    step = 0

    # connect to playwright mcp server, tells python to start MCP server
    # Defines HOW to start the MCP server — like writing the terminal command npx @playwright/mcp
    # but storing it as Python config instead of running it manually.
    server_params = StdioServerParameters(
        command="npx",
        args=["@playwright/mcp"]
    )

    print(f"Starting MCP agent for: {url}")
    print(f"Task: {task}")
    print("=" * 50)

    # stdio_client starts MCP server, open communication, handshake python and mcp
    # stdio_client(server_params)
    # → actually starts the MCP server as a subprocess
    # → opens two pipes: read (incoming data) and write (outgoing data)
    #
    # async with
    # → automatically closes the connection when block ends
    # → even if an error happens
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            # initialize mcp session
            # Wraps the read/write pipes into a proper session object
            # "session" is what we use for all future MCP calls
            # Like opening a structured phone call using the raw wires
            await session.initialize()
            # Handshake step:
            # Python says "hello, I'm ready"
            # MCP server says "hello, here's what I can do"
            # await = wait for this handshake to complete
            print("MCP session initialized!")

            # check available tools and their parameters
            tools = await session.list_tools()

            # Asks MCP server: "what tools do you have?"
            # Loops through and prints each tool name
            # Specifically prints full schema for click tool
            # This was debugging code we used to discover
            # the correct parameter names (target, not element)
            for tool in tools.tools:
                print(f"Available tool: {tool.name}")
                if "click" in tool.name:
                    print(f"Tool: {tool.name}")
                    print(f"Schema: {tool.inputSchema}")

            # navigate to url, MCP server tells playwright to go to url
            # await means wait for this to complete
            # Calls the browser_navigate MCP tool
            # Passes the url as parameter
            # MCP tells Playwright to open that URL
            # await = wait for navigation to complete
            await session.call_tool(
                "browser_navigate",
                {"url": url}
            )
            print(f"Navigated to {url}")

            # wait for page to fully load
            await asyncio.sleep(3)
            print("Page loaded!")

            while step < max_steps:
                step += 1
                print(f"\nStep {step}:")

                # get page snapshot
                # MCP server tells playwright, read page structure, this is text
                # Calls browser_snapshot MCP tool
                # {} = no parameters needed for this tool
                # Returns the full accessibility tree of current page
                snapshot_result = await session.call_tool(
                    "browser_snapshot", {}
                )
                print("snapshot result",snapshot_result)
                # snapshot_result is a complex object
                # .content is a list of content blocks
                # [0] takes first block
                # .text extracts the actual snapshot text
                snapshot = snapshot_result.content[0].text
                print("snapshot is",snapshot)

                # build message for claude
                # Adds a new message to our conversation list
                # role: "user" = this message is FROM us TO Claude
                # content = f-string with task, step, snapshot, and rules
                # IMPORTANT RULES:
                # 1. Always use ref numbers from snapshot
                #    Example: fill [ref=e23] with Admin
                conversation.append({
                    "role": "user",
                    "content": f"""
                    Task: {task}
                    Step: {step}
                    # 
                    
                    Current page structure:
                    {snapshot}
                    
                    IMPORTANT RULES:
                    1. Always use ref numbers from snapshot
                       Example: fill [ref=e23] with Admin
                    2. After login verify ALL of these before saying DONE:
                       - URL changed to /dashboard/index
                       - Dashboard heading is visible
                       - Navigation menu is visible
                       - No error messages on page
                    3. Only say DONE success if ALL verifications pass

                    
                    What should I do next?
                    Reply with EXACTLY one of:
                    ACTION: navigate to [url]
                    ACTION: click [element name]
                    ACTION: fill [element name] with [value]
                    ACTION: select [option] from [ref=eXX]
                    DONE: task completed successfully
                    DONE: task failed because [reason]
                    """
                })

                # ask claude what to do
                # client.messages.create() = the actual API call
                # model = which Claude version
                # max_tokens = limit response length to 500 tokens
                # messages = the FULL conversation history (not just latest message)
                response = client.messages.create(
                    model="claude-sonnet-4-5",
                    max_tokens=500,
                    messages=conversation
                )
                print("response here is ---", response)
                claude_decision = response.content[0].text
                print(f"Claude says: {claude_decision}")

                # save claude response to history
                conversation.append({
                    "role": "assistant",
                    "content": claude_decision
                })

                # check if done
                if "DONE:" in claude_decision:
                    passed = "completed successfully" in claude_decision
                    print(f"\nTest completed! Passed: {passed}")
                    return {
                        "passed": passed,
                        "reason": claude_decision,
                        "steps": step
                    }

                # execute claude's action via mcp
                if "ACTION:" in claude_decision:
                    action = claude_decision.split("ACTION:")[1].strip()
                    print(f"Executing: {action}")
                    await execute_mcp_action(session, action)

            # This only runs if the while loop exits naturally
            # (meaning step reached max_steps without Claude saying DONE)
            # Returns a failure result as a safety net
            return {
                "passed": False,
                "reason": f"Max steps reached. Last Claude response: {claude_decision}",
                "steps": step
            }

# Converts action text to lowercase so our if "click" in action_lower checks work regardless of capitalization.
async def execute_mcp_action(session, action):
    action_lower = action.lower()

    try:
        if "navigate to" in action_lower:
            url = action.split("navigate to")[1].strip()
            await session.call_tool(
                "browser_navigate",
                {"url": url}
            )

        elif "click" in action_lower:
            # First tries to find a ref=eXX pattern using regex
            # If found → use that exact ref
            # If not found → fall back to whatever text comes
            # after "click" (less reliable, used as backup)
            ref_match = re.search(r'ref=(e\d+)', action)
            if ref_match:
                ref = ref_match.group(1)
            else:
                ref = action.split("click")[1].strip()

            # Calls browser_click MCP tool
            # "target" is the required parameter (we learned this from schema)
            # "ref" is extra — kept for clarity/debugging
            # Prints the result so we can see success/failure
            print(f"Clicking: {ref}")
            result = await session.call_tool(
                "browser_click",
                {
                    "target": ref,
                    "ref": ref
                }
            )
            print(f"Click result: {result}")
            # give the page time to navigate/render after a click
            await asyncio.sleep(2)

        elif "fill" in action_lower:
            # extract ref number if claude provided it
            ref_match = re.search(r'ref=(e\d+)', action)
            ref = ref_match.group(1) if ref_match else ""

            # extract value after "with"
            # Splits on "with" to separate field-info from value
            # e.g. "fill [ref=e23] Username with Admin"
            # → parts = ["fill [ref=e23] Username ", " Admin"]
            # → value = "Admin"
            parts = action.split("with")
            value = parts[1].strip() if len(parts) > 1 else ""

            # extract element name
            name_part = parts[0]
            name = re.sub(r'\[ref=e\d+\]', '', name_part)
            name = name.replace("fill", "").strip()

            # use ref if available otherwise use name
            # re.sub() REMOVES the [ref=eXX] pattern from the name part
            # (so it doesn't get included as part of the field name)
            # Then removes the word "fill"
            # Then strips whitespace
            # Result: clean human-readable name like "Username"
            target = ref if ref else name

            print(f"Filling: target={target}, name={name}, value={value}")

            result = await session.call_tool(
                "browser_fill_form",
                {
                    "fields": [
                        {
                            "target": target,
                            "name": name if name else "field",
                            "type": "textbox",
                            "value": value
                        }
                    ]
                }
            )
            print(f"Fill result: {result}")

        elif "select" in action_lower:
            # extract ref if claude provided it
            ref_match = re.search(r'ref=(e\d+)', action)
            ref = ref_match.group(1) if ref_match else ""

            # extract option and element
            parts = action.split("from")
            option = parts[0].replace("select", "").strip()
            element_part = parts[1].strip() if len(parts) > 1 else ""

            # remove ref from element name if present
            element = re.sub(r'\[ref=e\d+\]', '', element_part).strip()

            # use ref if available otherwise use element name
            target = ref if ref else element

            print(f"Selecting: option={option}, target={target}")

            result = await session.call_tool(
                "browser_select_option",
                {"element": target, "value": option}
            )
            print(f"Select result: {result}")

    except Exception as e:
        print(f"Action failed: {e}")

        # get current snapshot
        snapshot_result = await session.call_tool(
            "browser_snapshot", {}
        )
        snapshot = snapshot_result.content[0].text

        # try to heal
        # Calls our heal_controller function
        # Passes: the original failed action,
        #         the current page structure,
        #         the error message as a string
        healed = heal_action(action, snapshot, str(e))

        # If Claude successfully found a healed action:
        #   Log it (original vs new)
        #   RECURSIVELY call execute_mcp_action again
        #   but this time with the HEALED action
        #
        # This is recursion — the function calls itself
        # with corrected parameters
        if healed:
            log_healing(action, healed)
            # retry with healed action
            await execute_mcp_action(session, healed)
        else:
            print("❌ Healing failed — cannot fix this automatically")


if __name__ == "__main__":
    result = asyncio.run(run_mcp_agent(
        "https://opensource-demo.orangehrmlive.com",
        "Login with username Admin and password admin123 and verify dashboard loads"
    ))

    # result = asyncio.run(test_self_healing())
    print(result)
    status = "✅ PASS" if result["passed"] else "❌ FAIL"
    print(f"\nFinal Result: {status}")
    print(f"Reason: {result['reason']}")
    print(f"Steps taken: {result['steps']}")



# Connects to Playwright MCP server
# ↓
# MCP server controls real browser
# ↓
# Gets page structure via browser_snapshot
# ↓
# Sends structure to Claude
# ↓
# Claude decides what to do next
# ↓
# Python executes via MCP tools
# ↓
# Loop until task complete
#


""""
Python starts MCP server automatically
        ↓
Python connects to MCP server
        ↓
MCP server starts Playwright browser
        ↓
Python tells MCP: "go to OrangeHRM"
        ↓
MCP tells Playwright: "navigate"
        ↓
Python tells MCP: "get page snapshot"
        ↓
MCP returns page structure as text
        ↓
Python sends structure to Claude
        ↓
Claude reads structure
Claude says: "fill Username with Admin"
        ↓
Python tells MCP: "fill Username with Admin"
        ↓
MCP tells Playwright: "fill field"
        ↓
Playwright types Admin in username field
        ↓
Python gets new snapshot
        ↓
Sends to Claude again
        ↓
Claude says: "fill Password with admin123"
        ↓
Repeat until Claude says DONE
"""


"""

"fill Username with Admin"
        ↓
split at "with"
        ↓
["fill Username ", " Admin"]
        ↓
parts[0] = "fill Username "  → remove "fill" → strip → "Username"
parts[1] = " Admin"          → strip → "Admin"

"""

"""
"I need to fill element ref=e23 with value Admin"
        ↓
MCP looks up ref=e23 in its internal page map
        ↓
Finds it's a textbox named "Username"
        ↓
MCP generates the best Playwright command:
await page.getByRole('textbox', { name: 'Username' }).fill('Admin')
        ↓
Executes it in browser
        ↓
Returns result to us

"""