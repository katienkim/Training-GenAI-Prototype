#!/usr/bin/env python3
import os
# CORRECTED: Import App and Environment directly from aws_cdk
from aws_cdk import App, Environment
from cdk_stack.cdk_stack import AiAuditorStack

# The CDK CLI will automatically use the credentials and region from your 'aws configure' profile.
env = Environment(
    account=os.getenv('CDK_DEFAULT_ACCOUNT'),
    region=os.getenv('CDK_DEFAULT_REGION')
)

app = App()
AiAuditorStack(app, "AiAuditorProdStack", env=env)

app.synth()
