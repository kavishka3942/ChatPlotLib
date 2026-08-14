import grpc
import os
from app.generated import executor_pb2
from app.generated import executor_pb2_grpc

class SandboxClient:
    def __init__(
        self,
        host: str | None = None,
        port: str | None = None
    ):

        self.host = host or os.getenv("SANDBOX_HOST","localhost")
        self.port = port or os.getenv( "SANDBOX_PORT","50051")
        self.address = f"{self.host}:{self.port}"
        self.channel = grpc.insecure_channel(self.address)
        self.stub = executor_pb2_grpc.CodeExecutorStub(self.channel)

    def execute(self,code: str):

        request = executor_pb2.CodeRequest(code=code)
        try:
            response = self.stub.ExecuteCode(request)
            return {

                "success": response.success,
                "stdout": response.stdout,
                "stderr": response.stderr,
                "plotly_json": response.plotly_json

            }


        except grpc.RpcError as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Sandbox gRPC error: {e.details()}",
                "plotly_json": ""
            }
    def close(self):

        self.channel.close()