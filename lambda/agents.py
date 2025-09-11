from strands import Agent
from tools.tools import audit_s3_buckets_for_compliance

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
    system_prompt="You are a specialized AWS security inspector. Your job is to use the tools you are given to fetch raw data about the AWS environment. Do not analyze or interpret the data.",
    tools=[audit_s3_buckets_for_compliance]
)

# The Analyst Agent interprets the raw data from the Inspector.
analyst_agent = Agent(
    system_prompt="You are a compliance analyst. You receive raw data in JSON format from an inspector. Your task is to analyze this data and create a simple summary of which resources are non-compliant and why.",
)

# The Reporter Agent makes the final report human-readable.
reporter_agent = Agent(
    system_prompt="You are a report writer. You receive a compliance analysis summary. Your job is to format this summary into a clear, concise, human-readable report. Provide a final answer and mention the sources or policies used.",
)

# The Orchestrator Agent manages the entire workflow.
orchestrator_agent = Agent(
    model="claude-opus-4-1-20250805-v1:0", # Use a powerful model for reasoning
    system_prompt=MAIN_SYSTEM_PROMPT,
    tools=[inspector_agent, analyst_agent, reporter_agent]
)