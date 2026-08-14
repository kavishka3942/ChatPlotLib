from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.agents.graph import app_graph
from app.services.storage import upload_file_to_minio
from langchain_core.messages import HumanMessage

app = FastAPI(title="AI Data Scientist Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    initial_state = {
        "messages": [HumanMessage(content=req.message)],
        "last_code": "",
        "execution_result": ""
    }
    
    # Await the async graph properly
    result = await app_graph.ainvoke(initial_state)
    
    last_message = result["messages"][-1].content if result["messages"] else "No response"
    return {"response": last_message}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    file_path = upload_file_to_minio(content, file.filename)
    return {"status": "success", "path": file_path}

@app.get("/")
def health_check():
    return {"status": "healthy", "layer": "Backend API Gateway"}