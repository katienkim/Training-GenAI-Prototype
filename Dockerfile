# Use the official AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.13

# Copy the requirements file
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install the Python dependencies
RUN pip install -r requirements.txt

# Copy the entire 'lambda' folder with all your Python code into the container
COPY lambda/ ${LAMBDA_TASK_ROOT}

# Set the command to run your Lambda handler function
CMD [ "orchestrator.lambda_handler" ]