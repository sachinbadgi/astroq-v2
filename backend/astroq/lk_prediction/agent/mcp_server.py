import os
import sys
import asyncio
from mcp.server.fastmcp import FastMCP

# Ensure the backend directory is in the Python path
_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from astroq.lk_prediction.agent.lk_agent import LalKitabAgent

# Initialize the MCP Server
mcp = FastMCP("AstroQ Deterministic Lal Kitab Engine")

@mcp.tool()
async def consult_lal_kitab_oracle(query: str, user_id: str = "default") -> str:
    """
    The exclusive and highly deterministic entry point for all Lal Kitab astrological tasks.
    Do NOT attempt to guess astrological calculations yourself. Pass the user's exact query
    to this tool. The backend will use mathematical vector search (SentenceTransformers)
    to decipher the intent, automatically load the correct chart (Natal, Annual, Monthly, Daily),
    and execute an internal rigid Graph network to derive an accurate answer.
    
    Args:
        query: The user's exact question (e.g., "What does my 40th year look like for career?")
        user_id: The client identifier string used to look up their chart. Default is "default".
    """
    # The LangGraph execution does dense compute and synchronous LLM calls.
    # We wrap it in to_thread so the async FastMCP server doesn't block.
    def run_deterministic_agent():
        agent = LalKitabAgent(user_id=user_id)
        return agent.ask(query)
        
    try:
        result = await asyncio.to_thread(run_deterministic_agent)
        return result
    except Exception as e:
        return f"The Lal Kitab oracle encountered an error protecting the deterministic execution: {str(e)}"


if __name__ == "__main__":
    # Start the standard MCP stdio server.
    print("Starting AstroQ Encapsulated MCP server (Deterministic Graph Mode).", file=sys.stderr)
    mcp.run(transport="stdio")
