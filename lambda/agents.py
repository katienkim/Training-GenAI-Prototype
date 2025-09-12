import os
from strands import Agent
from mcp.client import MCPClient

# --- MCP Server Client Configuration ---

# This URL must be provided to the Lambda function as an environment variable.
API_MCP_URL = os.environ.get("API_MCP_URL")
DOCS_MCP_URL = os.environ.get("DOCS_MCP_URL")
KNOWLEDGE_MCP_URL = os.environ.get("KNOWLEDGE_MCP_URL")
# Initialize tool lists
api_tools, docs_tools, knowledge_tools = [], [], []

# --- Connect to AWS API MCP Server ---
try:
    if not API_MCP_URL:
        raise ValueError("API_MCP_URL is not set.")
    api_client = MCPClient(base_url=API_MCP_URL)
    api_tools = api_client.tools
    print(f"Connected to API Server. Tools: {[tool.name for tool in api_tools]}")
except Exception as e:
    print(f"CRITICAL ERROR: Could not connect to AWS API MCP Server. Reason: {e}")

# --- Connect to AWS Documentation MCP Server ---
try:
    if not DOCS_MCP_URL:
        raise ValueError("DOCS_MCP_URL is not set.")
    docs_client = MCPClient(base_url=DOCS_MCP_URL)
    docs_tools = docs_client.tools
    print(f"Connected to Documentation Server. Tools: {[tool.name for tool in docs_tools]}")
except Exception as e:
    print(f"CRITICAL ERROR: Could not connect to AWS Documentation MCP Server. Reason: {e}")

# --- Connect to AWS Knowledge MCP Server ---
try:
    if not KNOWLEDGE_MCP_URL:
        raise ValueError("KNOWLEDGE_MCP_URL is not set.")
    knowledge_client = MCPClient(base_url=KNOWLEDGE_MCP_URL)
    knowledge_tools = knowledge_client.tools
    print(f"Connected to Knowledge Server. Tools: {[tool.name for tool in knowledge_tools]}")
except Exception as e:
    print(f"CRITICAL ERROR: Could not connect to AWS Knowledge MCP Server. Reason: {e}")

# --- Prompting ---
MAIN_SYSTEM_PROMPT = """
You are a master orchestrator for an AWS compliance audit. 
You will be given a user's query and you must process and route queries to the specialized agents in your team:
- First, for the retrieval of raw data from AWS resources → Use the inspector_agent tool.
- Second, pass the output of the inspector_agent to the analyst_agent tool for a compliance analysis.
- Third, pass the output from the analyst_agent to the reporter_agent to generate the final human-readable report.
- For simple questions not requiring specialized knowledge → Answer directly.

Always select the most appropriate tool based on the user's query.
"""

# --- Agent Definitions ---

# The Inspector Agent is a data gatherer. It only knows how to run its tools.
inspector_agent = Agent(
    model="claude-opus-4-1-20250805-v1:0", # Use a powerful model for data gathering
    system_prompt="You are a specialized AWS security inspector. Your job is to use the tools you are given to fetch raw data about the AWS environment. Do not analyze or interpret the data.",
    tools=api_tools
)

# The Analyst Agent interprets the raw data from the Inspector.
analyst_agent = Agent(
    model="claude-opus-4-1-20250805-v1:0", # Use a powerful model for data gathering
    system_prompt="You are a compliance analyst. You receive raw data in JSON format from an inspector. Your task is to analyze this data and create a simple summary of which resources are non-compliant and why.",
    tools=knowledge_tools
)

# The Reporter Agent makes the final report human-readable.
reporter_agent = Agent(
    model="claude-opus-4-1-20250805-v1:0", # Use a powerful model for data gathering
    system_prompt="You are a report writer. You receive a compliance analysis summary. Your job is to format this summary into a clear, concise, human-readable report. Provide a final answer and mention the sources or policies used.",
    tools=docs_tools
)