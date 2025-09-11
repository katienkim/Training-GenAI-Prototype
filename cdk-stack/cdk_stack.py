from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_apigatewayv2 as apigwv2,
    aws_ecr as ecr,
    aws_elasticloadbalancingv2 as elbv2,
    aws_s3_assets as s3_assets
)
from aws_cdk.aws_apigatewayv2_integrations import LambdaProxyIntegration

class AiAuditorStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # --- Backend: ECR Repository and Container-based Lambda ---

        # 1. Create an ECR repository to store our Lambda's container image
        ecr_repository = ecr.Repository(self, "AgentLambdaRepository")

        # 2. Define the Lambda function to use a Docker image from our ECR repo
        agent_lambda = _lambda.Function(self, "AgentLambda",
            code=_lambda.Code.from_ecr_image(
                repository=ecr_repository,
                # The CDK will automatically build the Dockerfile and push the image
                tag="latest" 
            ),
            handler=_lambda.Handler.FROM_IMAGE,
            runtime=_lambda.Runtime.FROM_IMAGE,
            timeout=core.Duration.seconds(60),
            memory_size=1024
        )
        
        # 3. API Gateway to trigger the Lambda
        http_api = apigwv2.HttpApi(self, "AgentHttpApi",
            cors_preflight=apigwv2.CorsPreflightOptions(allow_headers=["*"], allow_methods=[apigwv2.CorsHttpMethod.ANY], allow_origins=["*"])
        )
        http_api.add_routes(path="/", methods=[apigwv2.HttpMethod.POST], integration=LambdaProxyIntegration(handler=agent_lambda))

        # --- Frontend: Secure VPC with ALB and Private EC2 ---

        # 1. Create a VPC with public and private subnets
        vpc = ec2.Vpc(self, "StreamlitVpc", max_azs=2)

        # 2. Create an Application Load Balancer in the public subnet
        alb = elbv2.ApplicationLoadBalancer(self, "StreamlitALB", vpc=vpc, internet_facing=True)
        listener = alb.add_listener("PublicListener", port=80, open=True)

        # The UserData script
        user_data = ec2.UserData.for_linux()

        git_repo_url = ""
        app_dir = ""

        user_data.add_commands(
            # 1. Install Dependencies
            "yum update -y",
            "yum install -y git python3-pip",

            # 2. Get Application Code
            f"git clone {git_repo_url} {app_dir}",
            f"cd {app_dir}/streamlit_ui",

            # 3. Install Python Libraries
            "pip3 install -r requirements.txt",
            
            # 4. Set Environment Variable for the API URL
            # The http_api.url comes from the API Gateway construct defined earlier in the stack
            f"echo 'API_ENDPOINT_URL={http_api.url}' > .env",

            # 5. Create and run the systemd service for persistence
            """
            cat <<EOF > /etc/systemd/system/streamlit.service
            [Unit]
            Description=Streamlit AI Auditor App
            After=network.target
            [Service]
            User=ec2-user
            EnvironmentFile={app_dir}/streamlit_ui/.env
            WorkingDirectory={app_dir}/streamlit_ui/
            ExecStart=/usr/local/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.enableCORS false
            [Install]
            WantedBy=multi-user.target
            EOF
            """,
            "systemctl daemon-reload",
            "systemctl enable streamlit.service",
            "systemctl start streamlit.service"
        )

        # 3. Define the EC2 instance for Streamlit
        instance = ec2.Instance(self, "StreamlitInstance",
            vpc=vpc,
            # Place the instance in a private subnet for security
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
            machine_image=ec2.AmazonLinuxImage(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2),
            user_data=user_data
        )

        # 4. Add the EC2 instance as a target for the ALB
        listener.add_targets("EC2Target",
            port=8501, # Traffic from ALB to EC2 is on streamlit's port
            targets=[instance]
        )

        # --- CDK Outputs ---
        core.CfnOutput(self, "ApiEndpointURL", value=http_api.url)
        # The user will access the app via the Load Balancer's DNS name
        core.CfnOutput(self, "StreamlitAppURL", value=f"http://{alb.load_balancer_dns_name}")