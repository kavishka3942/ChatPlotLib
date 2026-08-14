FROM python:3.10-slim
WORKDIR /app

# Tell Python that /app is the root for imports
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y gcc

# 1. Copy requirements and install (with build cache for speed)
COPY sandbox/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# 2. Copy sandbox code
COPY sandbox/executor ./executor
COPY sandbox/generated ./generated

# 3. Copy the shared proto file from the root context
COPY proto ./proto

# 4. Generate gRPC code into the executor folder
RUN python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./generated \
    --grpc_python_out=./generated \
    ./proto/executor.proto

RUN sed -i 's/^import executor_pb2/from . import executor_pb2/' \
    generated/executor_pb2_grpc.py

CMD ["python", "-u", "-m", "executor.server"]