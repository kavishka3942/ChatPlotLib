from fastapi import FastAPI, UploadFile, File
import json
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict
from app.agents.graph import app_graph
from app.services.storage import upload_file_to_minio, get_dataset_schema
from langchain_core.messages import HumanMessage, AIMessage

app = FastAPI(title="AI Data Scientist Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LATEST_DATASET_INFO = {
    "filename": "",
    "schema": "",
    "path": ""
}

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    filename: str = ""
    dataset_schema: str = ""

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    filename = req.filename or LATEST_DATASET_INFO["filename"]
    schema = req.dataset_schema or LATEST_DATASET_INFO["schema"]

    langchain_messages = []
    for msg in req.messages:
        if msg["role"] == "user":
            langchain_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            langchain_messages.append(AIMessage(content=msg["content"]))

    initial_state = {
        "messages": langchain_messages,
        "last_code": "",
        "execution_result": "",
        "filename": filename,
        "dataset_schema": schema,
        "retries": 0
    }
    
    async def generate():
        async for event in app_graph.astream_events(initial_state, version="v2"):
            kind = event["event"]
            node = event.get("metadata", {}).get("langgraph_node")
            
            if kind == "on_chat_model_stream" and node == "chat":
                content = event["data"]["chunk"].content
                if content:
                    yield json.dumps({"type": "token", "content": content}) + "\n"

            elif kind == "on_chain_stream" and node in ["respond", "respond_code"]:
                chunk = event["data"]["chunk"]
                if "messages" in chunk and chunk["messages"]:
                    yield json.dumps({"type": "text", "content": chunk["messages"][-1].content}) + "\n"
                
                if "plotly_json" in chunk and chunk["plotly_json"]:
                    yield json.dumps({"type": "plotly", "content": chunk["plotly_json"]}) + "\n"

    return StreamingResponse(generate(), media_type="text/plain")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    file_path = upload_file_to_minio(content, file.filename)
    schema = get_dataset_schema(content, file.filename)
    
    LATEST_DATASET_INFO["filename"] = file.filename
    LATEST_DATASET_INFO["schema"] = schema
    LATEST_DATASET_INFO["path"] = file_path

    return {
        "status": "success",
        "filename": file.filename,
        "path": file_path,
        "schema": schema
    }

@app.get("/")
def health_check():
    return {"status": "healthy", "layer": "Backend API Gateway"}