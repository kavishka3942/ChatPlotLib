from typing import TypedDict
from langgraph.graph import (StateGraph,END)
from langchain_core.messages import (AIMessage)
from app.services.llm import call_ollama
from app.services.sandbox_client import (SandboxClient)
from app.services.utility import (clean_python_code)

# -------------------------
# State
# -------------------------

class AgentState(TypedDict):
    messages: list
    last_code: str
    sandbox_success: bool
    stdout: str
    stderr: str
    plotly_json: str
# -------------------------
# Services
# -------------------------
sandbox = SandboxClient()
# -------------------------
# Nodes
# -------------------------
async def chat_node(state: AgentState):
    msg = state["messages"][-1].content
    response = await call_ollama(msg)
    return {
        "messages":[AIMessage(content=response)]
    }   
async def code_generator_node(state: AgentState):
    user_query = (state["messages"][-1].content)
    prompt=f"""

You are a Python data analyst.
Generate only executable Python code.
No markdown.
No explanations.
User request:
{user_query}
"""
    code = await call_ollama(prompt)
    code = clean_python_code(code)
    return {"last_code": code}

async def execution_node(state: AgentState):
    result = sandbox.execute(state["last_code"])
    return {
        "sandbox_success":result["success"],
        "stdout":result["stdout"],
        "stderr":result["stderr"],
        "plotly_json":result["plotly_json"]
    }

async def response_node(state: AgentState):
    if state["sandbox_success"]:
        content = state["stdout"]
        if state["plotly_json"]:
            content += ( "\nChart generated.")

    else:
        content = ("Execution failed:\n" + state["stderr"])

    return {
        "messages":[
            AIMessage(content=content)
        ]
    }
# -------------------------
# Router
# -------------------------
def router(state: AgentState):
    text = (state["messages"][-1].content.lower())
    
    if ("hello" in text or "hi" in text):
        return "chat"
    return "code"
# -------------------------
# Graph
# -------------------------
workflow = StateGraph(AgentState)
workflow.add_node("chat",chat_node)
workflow.add_node("generate_code",code_generator_node)
workflow.add_node("execute",execution_node)
workflow.add_node("respond",response_node)
workflow.set_conditional_entry_point(
    router,
    {
        "chat":"chat",
        "code":"generate_code"
    }
)
workflow.add_edge("chat",END)
workflow.add_edge("generate_code","execute")
workflow.add_edge("execute","respond")
workflow.add_edge("respond",END)

app_graph = workflow.compile()