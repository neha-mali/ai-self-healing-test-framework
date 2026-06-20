import anthropic
import os
from dotenv import load_dotenv

# Actually loads the .env file into memory so os.getenv() calls can find the API key
load_dotenv()


def get_claude_client():
    # creates and returns anthropic client
    # using API key from .env file
    client = anthropic.Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )
    return client



'''

claude_agent.py says:
"Give me a Claude client"
        ↓
mcp_client.py returns the client
        ↓
claude_agent.py says:
"Give me the MCP server config"
        ↓
mcp_client.py returns the config
        ↓
claude_agent.py connects Claude to browser
        ↓
Claude can now control the browser

'''