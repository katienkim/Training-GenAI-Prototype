from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_apigatewayv2 as apigwv2,
    aws_ecr as ecr,
    aws_elasticloadbalancingv2 as elbv2,
    aws_elasticloadbalancingv2_targets as elbv2_targets
)
from aws_cdk.aws_lambda import Code
from aws_cdk.aws_apigatewayv2_integrations import HttpLambdaIntegration
from constructs import Construct

class AiAuditorStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # --- CDK Parameters for MCP Server URLs ---
        # api_mcp_url = core.CfnParameter(self, "ApiMcpUrl", type="String", description="URL for the AWS API MCP Server")
        # docs_mcp_url = core.CfnParameter(self, "DocsMcpUrl", type="String", description="URL for the AWS Docs MCP Server")
        knowledge_mcp_url = "https://knowledge-mcp.global.api.aws" 

        # --- Backend: ECR, Lambda, API Gateway ---

        # 1. Create an ECR repository to store our Lambda's container image
        ecr_repository = ecr.Repository(self, "AgentLambdaRepository")

        # 2. Define the Lambda function to use a Docker image from our ECR repository
        agent_lambda = _lambda.Function(self, "AgentLambda",
            code=_lambda.Code.from_asset("lambda"),
            # handler=_lambda.Handler.FROM_IMAGE,
            handler="orchestrator.lambda_handler",
            # runtime=_lambda.Runtime.FROM_IMAGE,
            # architecture=_lambda.Architecture.ARM_64,
            runtime=_lambda.Runtime.PYTHON_3_13,
            timeout=Duration.seconds(60),
            memory_size=1024,
            environment={
                # "API_MCP_URL": api_mcp_url.value_as_string,
                # "DOCS_MCP_URL": docs_mcp_url.value_as_string,
                "KNOWLEDGE_MCP_URL": knowledge_mcp_url
            }
        )

        # Grant the Lambda permission to invoke the Bedrock model
        agent_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=[f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-opus-4-1-20250805-v1:0"]
        ))

        # Grant the Lambda read-only access to AWS resources for inspection
        agent_lambda.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("ReadOnlyAccess")
        )
        
        # 3. API Gateway to trigger the Lambda
        http_api = apigwv2.HttpApi(self, "AgentHttpApi",
            cors_preflight=apigwv2.CorsPreflightOptions(allow_headers=["*"], allow_methods=[apigwv2.CorsHttpMethod.ANY], allow_origins=["*"])
        )
        http_api.add_routes(
            path="/",
            methods=[apigwv2.HttpMethod.POST],
            integration=HttpLambdaIntegration("AgentLambdaIntegration", handler=agent_lambda)
        )

        # --- Frontend: Secure VPC with ALB and Private EC2 ---

        # 1. Create a VPC with public and private subnets
        vpc = ec2.Vpc(self, "StreamlitVpc", max_azs=2, subnet_configuration=[
            # By defining a PUBLIC subnet, the CDK automatically creates and configures the Internet Gateway.
            ec2.SubnetConfiguration(name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24),
            ec2.SubnetConfiguration(name="Private", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, cidr_mask=24)
        ])
        alb = elbv2.ApplicationLoadBalancer(self, "StreamlitALB", vpc=vpc, internet_facing=True)
        listener = alb.add_listener("PublicListener", port=80, open=True)
        instance_sg = ec2.SecurityGroup(self, "InstanceSG", vpc=vpc)
        instance_sg.connections.allow_from(alb, ec2.Port.tcp(8501), "Allow Streamlit traffic from ALB")
        git_repo_url = "https://github.com/katienkim/Training-GenAI-Prototype.git"

        # 1. Open and read the script file
        with open("./configure_streamlit.sh", "r") as f:
            user_data_script = f.read()

        # 2. Initialize the UserData object
        user_data = ec2.UserData.for_linux()

        # 3. Add the script content to the UserData object, replacing the placeholder
        user_data.add_commands(
            user_data_script.replace("##API_ENDPOINT_URL##", http_api.url)
        )

        # 3. Define the EC2 instance for Streamlit
        instance = ec2.Instance(self, "StreamlitInstanceV1",
            vpc=vpc,
            instance_type=ec2.InstanceType("t3.micro"),
            # machine_image=ec2.AmazonLinuxImage(
            #     generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
            #     cpu_type=ec2.AmazonLinuxCpuType.ARM_64
            # ),
            machine_image=ec2.AmazonLinuxImage(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2023, cpu_type=ec2.AmazonLinuxCpuType.X86_64),
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_group=instance_sg, user_data=user_data
        )

        instance.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")
        )

        # 4. Add the EC2 instance as a target for the ALB
        listener.add_targets("EC2Target",
            port=8501,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[elbv2_targets.InstanceTarget(instance)],
            # --- ADD THIS HEALTH CHECK CONFIGURATION ---
            health_check=elbv2.HealthCheck(
                path="/healthz",  # Use Streamlit's built-in health check endpoint
                healthy_threshold_count=2,
                unhealthy_threshold_count=5,
                interval=Duration.seconds(30),
            )
        )

        # --- CDK Outputs ---
        CfnOutput(self, "AppURL", value=f"http://{alb.load_balancer_dns_name}", description="The URL for the Streamlit UI")
        CfnOutput(self, "ApiEndpointURL", value=http_api.url, description="The endpoint for the backend agent API")
        CfnOutput(self, "EcrRepositoryName", value=ecr_repository.repository_name, description="The name of the ECR repository for the Lambda image")