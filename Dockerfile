# Use a stable, supported AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.13

# Copy the backend requirements file into the container's task root
COPY lambda/requirements.txt ${LAMBDA_TASK_ROOT}

# Install the Python dependencies
RUN pip install -r requirements.txt

# Copy the entire 'lambda' folder with all backend Python code into the container
COPY lambda/ ${LAMBDA_TASK_ROOT}

# Set the command that Lambda will run. This points to the lambda_handler function
# inside the orchestrator.py file.
CMD [ "orchestrator.lambda_handler" ]