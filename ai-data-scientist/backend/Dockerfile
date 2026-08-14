FROM python:3.10-slim
WORKDIR /app

# Tell Python that /app is the root for imports
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y gcc

# 1. Copy requirements and install (with build cache for speed)
COPY backend/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# 2. Copy backend code
COPY backend/app ./app

# 3. Copy the shared proto file from the root context
COPY proto ./proto

# 4. Generate gRPC code into the services folder
RUN python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./app/generated \
    --grpc_python_out=./app/generated \
    ./proto/executor.proto
RUN sed -i 's/^import executor_pb2/from . import executor_pb2/' \
    ./app/generated/executor_pb2_grpc.py

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]