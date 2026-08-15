import asyncio
from langchain_core.messages import HumanMessage
from app.agents.graph import app_graph

async def main():
    initial_state = {
        "messages": [HumanMessage(content="hi")],
        "last_code": "",
        "execution_result": "",
        "filename": "",
        "dataset_schema": "",
        "retries": 0
    }
    
    async for event in app_graph.astream_events(initial_state, version="v2"):
        print(f"Event: {event['event']} Node: {event.get('metadata', {}).get('langgraph_node')}")
        if event["event"] == "on_chat_model_stream":
            print("  Chunk content:", repr(event["data"]["chunk"].content))

if __name__ == "__main__":
    asyncio.run(main())
