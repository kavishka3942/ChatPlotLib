import asyncio
from langchain_core.messages import HumanMessage
from app.agents.graph import app_graph

async def main():
    initial_state = {
        "messages": [HumanMessage(content="what is 2+2?")],
        "last_code": "",
        "execution_result": "",
        "filename": "",
        "dataset_schema": "",
        "retries": 0
    }
    
    async for event in app_graph.astream_events(initial_state, version="v2"):
        kind = event["event"]
        node = event.get("metadata", {}).get("langgraph_node")
        if node == "respond" and kind == "on_chain_stream":
            print("Respond chunk:", repr(event["data"]["chunk"]))

if __name__ == "__main__":
    asyncio.run(main())
