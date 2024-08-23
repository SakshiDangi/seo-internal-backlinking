FROM public.ecr.aws/lambda/python:3.11

COPY rag_agent/requirements.txt ./
RUN python3.11 -m pip install --upgrade pip
RUN python3.11 -m pip install -r requirements.txt -t .

COPY common/ ./common/
COPY predefined_tool/ ./predefined_tool/
COPY rag_agent/ ./rag_agent/

# Command can be overwritten by providing a different command in the template directly.
CMD ["rag_agent.app.lambda_handler"]