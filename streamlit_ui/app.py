import requests
import json
import os
import streamlit as st

# The CDK script will pass the API Gateway URL as an environment variable to the EC2 instance.
API_ENDPOINT_URL = os.environ.get("API_ENDPOINT_URL")

def call_auditor_agent(prompt: str) -> str:
    """Sends the user's query to the backend agent and returns the response."""
    if not API_ENDPOINT_URL:
        return "## ERROR\nAPI Endpoint URL is not configured. The backend is unreachable."

    headers = {'Content-Type': 'application/json'}
    payload = {'query': prompt}

    try:
        # Call the deployed API Gateway endpoint, which triggers the Lambda
        response = requests.post(API_ENDPOINT_URL, headers=headers, data=json.dumps(payload), timeout=60)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        response_data = response.json()
        
        # Format the response for display in the UI
        answer = response_data.get("answer", "No answer found.")
        sources = response_data.get("sources", "No sources provided.")
        return f"## Answer\n{answer}\n\n---\n\n### Sources\n{sources}"

    except requests.exceptions.RequestException as e:
        return f"## API Connection ERROR\nCould not connect to the agent backend. Please check the service status.\n\nDetails: {e}"
    except Exception as e:
        return f"## ERROR\nAn unexpected error occurred: {e}"

# --- Streamlit User Interface ---
st.set_page_config(page_title="AI Compliance Auditor", page_icon="📑", layout="centered")

st.title("📑 AI Compliance Auditor")
st.markdown("Ask a question about your AWS environment's compliance. The system will retrieve live data and provide a sourced answer.")

# Use a form for a cleaner UI experience
with st.form("audit_query_form"):
    user_query = st.text_area("Your Compliance Question:", placeholder="e.g., Audit all S3 buckets for versioning and encryption.", height=120)
    submitted = st.form_submit_button("Run Audit")

if submitted and user_query.strip():
    with st.spinner("Auditing environment... This may take a moment."):
        result = call_auditor_agent(user_query)
    st.markdown(result)
elif submitted:
    st.warning("⚠️ Please enter a question before submitting.")