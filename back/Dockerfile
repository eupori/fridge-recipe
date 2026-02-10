FROM public.ecr.aws/lambda/python:3.11

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app
COPY handler.py .

# Ensure Python can find the app module
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}"

# Set the CMD to handler
CMD [ "handler.handler" ]
