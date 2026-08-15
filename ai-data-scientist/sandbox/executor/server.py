import grpc
from concurrent import futures
import time
import sys
import io
import json
import pandas as pd
# pyrefly: ignore [missing-import]
import plotly.express as px

import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated"))

# pyrefly: ignore [missing-import]
import executor_pb2
# pyrefly: ignore [missing-import]
import executor_pb2_grpc
# pyrefly: ignore [missing-import]
import boto3
from botocore.client import Config

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "ai-data-scientist")


def sync_files_from_minio():
    # 1. Sync from local backend/uploads directory if present
    backend_uploads = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend", "uploads"))
    if os.path.exists(backend_uploads):
        import shutil
        for f in os.listdir(backend_uploads):
            src = os.path.join(backend_uploads, f)
            if os.path.isfile(src):
                shutil.copy(src, f)

    # 2. Sync from MinIO if available
    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=f"http://{MINIO_ENDPOINT}",
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
        response = s3.list_objects_v2(Bucket=BUCKET_NAME)
        if "Contents" in response:
            for obj in response["Contents"]:
                key = obj["Key"]
                s3.download_file(BUCKET_NAME, key, key)
    except Exception:
        pass  # MinIO offline; fallback to local workspace uploads


class CodeExecutorServicer(executor_pb2_grpc.CodeExecutorServicer):
    def ExecuteCode(self, request, context):
        code = request.code
        print(f"🚀 Executing code:\n{code}")

        # Ensure files from MinIO are downloaded locally
        sync_files_from_minio()
        
        # Capture stdout and stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = mystdout = io.StringIO()
        sys.stderr = mystderr = io.StringIO()
        
        success = True
        
        # Create a namespace for the executed code
        code_namespace = {
            "pd": pd,
            "px": px,
            "json": json
        }
        
        plotly_json = ""
        try:
            # Execute the AI-generated code
            exec(code, code_namespace)
            if "fig" in code_namespace and hasattr(code_namespace["fig"], "to_json"):
                fig_obj = code_namespace["fig"]
                if callable(getattr(fig_obj, "to_json", None)):
                    plotly_json = fig_obj.to_json()
        except Exception as e:
            success = False
            print(str(e), file=sys.stderr)
        finally:
            # Restore stdout and stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            
        return executor_pb2.CodeResponse(
            stdout=mystdout.getvalue(),
            stderr=mystderr.getvalue(),
            plotly_json=plotly_json,
            success=success
        )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    executor_pb2_grpc.add_CodeExecutorServicer_to_server(CodeExecutorServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("✅ Sandbox Execution Layer is listening on port 50051...", flush=True)
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()