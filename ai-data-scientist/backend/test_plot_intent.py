import asyncio
from langchain_core.messages import HumanMessage
from app.agents.graph import app_graph

async def main():
    initial_state1 = {
        "messages": [HumanMessage(content="calculate the mean of age")],
        "last_code": "",
        "execution_result": "",
        "filename": "",
        "dataset_schema": "",
        "retries": 0,
        "intent": "",
        "needs_plot": False
    }
    
    initial_state2 = {
        "messages": [HumanMessage(content="plot a scatter graph of age vs income")],
        "last_code": "",
        "execution_result": "",
        "filename": "",
        "dataset_schema": "",
        "retries": 0,
        "intent": "",
        "needs_plot": False
    }
    
    print("Test 1 (No Plot):")
    result1 = await app_graph.ainvoke(initial_state1)
    print("Intent:", result1.get("intent"), "Needs Plot:", result1.get("needs_plot"))
    print("Code Generated:", repr(result1.get("last_code", "")))
    
    print("\nTest 2 (Plot):")
    result2 = await app_graph.ainvoke(initial_state2)
    print("Intent:", result2.get("intent"), "Needs Plot:", result2.get("needs_plot"))
    print("Code Generated:", repr(result2.get("last_code", "")))

if __name__ == "__main__":
    asyncio.run(main())
