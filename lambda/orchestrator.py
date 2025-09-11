from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent
from analyst import analyst_agent
from reporter import reporter_agent
import logging

from inspector import list_s3_buckets, list_ec2_instances, list_iam_users

app = BedrockAgentCoreApp()


orchestrator_agent = Agent(
    model="claude-opus-4-1-20250805-v1:0",
    system_prompt=MAIN_SYSTEM_PROMPT,
    callback_handler=None,
    tools=[inspector_agent, analyst_agent, reporter_agent]
)

@app.entrypoint
async def orchestrator(payload):
    """Orchestrator agent function"""
    logging.info(f"Agent invocation payload: {payload}")
    try:
        user_message = payload.get("prompt", "Hello! How can I help you today?")
        if not user_message:
            return {"error": "Prompt not provided in payload."}
        result = orchestrator_agent(user_message)
        return {"result": result.message}
    except Exception as e:
        logging.error(f"An unexpected error occured: {e}", exc_info=True)
        return {"error": "An internal error occurred. Please try again later."}

if __name__ == "__main__":
    app.run()

'''
def lambda_handler(event, context):
    """
    This function is the entrypoint for the AWS Lambda.
    It receives the HTTP request from API Gateway, extracts the user's query,
    invokes the orchestrator, and returns a properly formatted HTTP response.
    """
    try:
        body = json.loads(event.get('body', '{}'))
        # Use 'query' to match the key from the frontend
        user_query = body.get('query')

        if not user_query:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'A "query" is required in the request body.'})
            }

        response_body = run_orchestration(user_query)
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps(response_body)
        }

    except Exception as e:
        print(f"An error occurred: {e}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': f'An internal server error occurred: {str(e)}'})
        }
'''