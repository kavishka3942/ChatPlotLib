# pyrefly: ignore [missing-import]
import chainlit as cl
import httpx
import pandas as pd
# pyrefly: ignore [missing-import]
import plotly.express as px
import plotly.io as pio

import os
import json

# Configuration: URL where your FastAPI backend is running
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# --- 1. File Upload & Chat Start Handler ---
@cl.on_chat_start
async def start():
    cl.user_session.set("history", [])
    await cl.Message(content="👋 Hi! I'm your AI Data Scientist. You can chat with me or upload a CSV/Excel file to get started!").send()

@cl.on_message
async def main(message: cl.Message):
    user_msg = message.content
    
    # --- A. Handle File Uploads (if the user attached files) ---
    if message.elements:
        for element in message.elements:
            # Chainlit File elements have a 'path' attribute pointing to the temp file
            if hasattr(element, 'path') and element.path:
                with open(element.path, "rb") as f:
                    # FastAPI expects the form-data key to be "file"
                    files = {"file": (element.name, f)}
                    
                    async with httpx.AsyncClient() as client:
                        upload_res = await client.post(f"{BACKEND_URL}/upload", files=files)
                        
                        if upload_res.status_code == 200:
                            res_data = upload_res.json()
                            filename = res_data.get("filename", element.name)
                            schema = res_data.get("schema", "")
                            cl.user_session.set("filename", filename)
                            cl.user_session.set("dataset_schema", schema)
                            
                            msg_content = f"✅ File **'{filename}'** uploaded successfully to backend & MinIO!"
                            if schema:
                                msg_content += f"\n\n```text\n{schema}\n```"
                            await cl.Message(content=msg_content).send()
                        else:
                            await cl.Message(content=f"❌ Upload failed: {upload_res.text}").send()

    # --- B. Handle Text Chat ---
    if user_msg:
        history = cl.user_session.get("history", [])
        history.append({"role": "user", "content": user_msg})

        async with httpx.AsyncClient() as client:
            try:
                # Call the FastAPI /chat endpoint with active dataset session context
                payload = {
                    "messages": history,
                    "filename": cl.user_session.get("filename", ""),
                    "dataset_schema": cl.user_session.get("dataset_schema", "")
                }
                
                msg = cl.Message(content="")
                await msg.send()
                
                async with client.stream(
                    "POST",
                    f"{BACKEND_URL}/chat", 
                    json=payload,
                    timeout=60.0 
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            if data["type"] in ["token", "text"]:
                                await msg.stream_token(data["content"])
                            elif data["type"] == "plotly":
                                plotly_json = data["content"]
                                if plotly_json:
                                    fig = pio.from_json(plotly_json)
                                    msg.elements = [cl.Plotly(name="chart", figure=fig, display="inline")]
                        except Exception as e:
                            print(f"Error parsing line: {line} - {e}")
                
                await msg.update()
                
                # Append assistant response to history
                history.append({"role": "assistant", "content": msg.content})
                cl.user_session.set("history", history)
                
            except httpx.HTTPStatusError as e:
                await cl.Message(content=f"❌ Backend error: {e.response.status_code} - {e.response.text}").send()
            except httpx.ConnectError:
                await cl.Message(content=f"❌ Could not connect to backend at {BACKEND_URL}. Is the FastAPI server running?").send()
            except Exception as e:
                await cl.Message(content=f"❌ An unexpected error occurred: {str(e)}").send()

# --- 2. Displaying Artifacts (Charts & Tables) ---
# (Kept for future use when your backend starts returning chart data)
async def display_sample_data():
    df = pd.DataFrame({
        "Category": ["A", "B", "C", "D"],
        "Values": [10, 25, 15, 30]
    })
    table = cl.Table(data=df.to_dict(orient="records"), name="Sample Data")
    fig = px.bar(df, x="Category", y="Values", title="Sample Analysis")
    plotly_chart = cl.Plotly(name="chart", figure=fig)
    await cl.Message(content="Sample data", elements=[table, plotly_chart]).send()