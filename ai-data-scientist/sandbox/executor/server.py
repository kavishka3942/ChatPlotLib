import grpc
from concurrent import futures
import time
import sys
import io
import json
import pandas as pd
# pyrefly: ignore [missing-import]
import plotly.express as px

from generated import executor_pb2
from generated import executor_pb2_grpc

class CodeExecutorServicer(executor_pb2_grpc.CodeExecutorServicer):
    def ExecuteCode(self, request, context):
        code = request.code
        print(f"🚀 Executing code:\n{code}")
        
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
        
        try:
            # Execute the AI-generated code
            exec(code, code_namespace)
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
            plotly_json="",
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