# pyrefly: ignore [missing-import]
import chainlit as cl
import httpx
import pandas as pd
# pyrefly: ignore [missing-import]
import plotly.express as px

# Configuration: URL where your FastAPI backend is running
BACKEND_URL = "http://backend:8000"

# --- 1. File Upload & Chat Start Handler ---
@cl.on_chat_start
async def start():
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
                            await cl.Message(content=f"✅ File '{element.name}' uploaded successfully to the backend!").send()
                        else:
                            await cl.Message(content=f"❌ Upload failed: {upload_res.text}").send()

    # --- B. Handle Text Chat ---
    if user_msg:
        async with httpx.AsyncClient() as client:
            try:
                # Call the FastAPI /chat endpoint with a 60s timeout (LLMs can be slow)
                response = await client.post(
                    f"{BACKEND_URL}/chat", 
                    json={"message": user_msg},
                    timeout=60.0 
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract the AI response and send it to the UI
                ai_response = data.get("response", "No response from AI.")
                await cl.Message(content=ai_response).send()
                
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
    await table.send()

    fig = px.bar(df, x="Category", y="Values", title="Sample Analysis")
    plotly_chart = cl.Plotly(name="chart", figure=fig)
    await plotly_chart.send()