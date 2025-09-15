import os
from strands import Agent
from mcp.client import MCPClient
from awslabs import aws_api_mcp_server
from awslabs import aws_documentation_mcp_server

# --- MCP Server Client Configuration ---

# This URL must be provided to the Lambda function as an environment variable.
# API_MCP_URL = os.environ.get("API_MCP_URL")
# DOCS_MCP_URL = os.environ.get("DOCS_MCP_URL")
KNOWLEDGE_MCP_URL = os.environ.get("KNOWLEDGE_MCP_URL")
# Initialize tool lists
api_tools, docs_tools, knowledge_tools = [], [], []

# --- Connect to AWS API MCP Server ---
try:
    api_client = MCPClient(aws_api_mcp_server.DEFAULT_API_MCP_URL)
    api_tools = api_client.tools
    print(f"Connected to API Server. Tools: {[tool.name for tool in api_tools]}")
except Exception as e:
    print(f"CRITICAL ERROR: Could not connect to AWS API MCP Server. Reason: {e}")

# --- Connect to AWS Documentation MCP Server ---
try:
    docs_client = MCPClient(aws_documentation_mcp_server.DEFAULT_DOCS_MCP_URL)
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
    system_prompt="""
    You are a specialized AWS inspector bot. Based on the user's request, you must use the available tools to fetch raw configuration data about the AWS environment.
    Your final response MUST be ONLY the raw JSON output from the tool.
    Do NOT include any conversational text, explanations, or markdown formatting like ```json.
    If the tool returns an empty list or an error, return an empty JSON object: {}.
    If the user's request is not related to AWS resource inspection, respond with: {"message": "No inspection needed."}
    Always respond in valid JSON format.
    """,
    tools=api_tools
)

# The Analyst Agent interprets the raw data from the Inspector.
analyst_agent = Agent(
    model="claude-opus-4-1-20250805-v1:0", # Use a powerful model for data gathering
    system_prompt="""
    You are a specialized compliance analyst. You will receive raw AWS resource data in JSON format.
    Your task is to analyze this data against standard security and cost best practices.
    Create a concise summary of non-compliant resources and explain WHY they are non-compliant.
    Your output should be a clear, human-readable text analysis.
    If the input data is empty or contains {"message": "No inspection needed."}, respond with: {"analysis": "No analysis needed."}.
    Always respond in valid JSON format.
    """,
    tools=knowledge_tools
)

# The Reporter Agent makes the final report human-readable.
reporter_agent = Agent(
    model="claude-opus-4-1-20250805-v1:0", # Use a powerful model for data gathering
    system_prompt="""
    You are a specialized technical report writer. You will receive a compliance analysis summary.
    Your job is to format this summary into a clear, concise, final, human-readable report.
    Use your documentation tools to find and include brief, step-by-step remediation advice for the identified issues.
    Structure the report clearly with headings for each finding.
    Provide a final answer and mention the sources or policies used.
    If the input analysis is empty or contains {"analysis": "No analysis needed."}, respond with: {"final_report": "No report needed."}.
    Always respond in valid JSON format.
    """,
    tools=docs_tools
)