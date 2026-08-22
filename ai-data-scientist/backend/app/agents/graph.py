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
    dataset_schema: str
    filename: str
    retries: int
    intent: str
    needs_plot: bool
# -------------------------
# Services
# -------------------------
sandbox = SandboxClient()
# -------------------------
# Nodes
# -------------------------
async def detect_intent_node(state: AgentState):
    text = state["messages"][-1].content
    prompt = f"""
You are an intent classification agent. Analyze the user's message and determine their intent.
The user is interacting with an AI Data Scientist.

Categories for 'intent':
1. 'chat': The user is greeting, asking casual questions (e.g., "what is your name", "who are you"), or having a normal conversation.
2. 'execute': The user wants to analyze data, create a plot, train a model, or get the result/output of some calculation.
3. 'code': The user specifically asks for Python code to be written for them to look at, without asking for the result of running it.

You also need to determine if the user explicitly requested a plot/graph/visualization.
Set 'needs_plot' to true ONLY IF the user explicitly asked for a visualization. Otherwise false.

Respond ONLY with a valid JSON object matching this schema:
{{
    "intent": "chat" | "execute" | "code",
    "needs_plot": true | false
}}

User message: {text}
"""
    import json
    response = await call_ollama(prompt)
    try:
        clean_response = response.strip()
        if clean_response.startswith("```json"):
            clean_response = clean_response[7:]
        if clean_response.startswith("```"):
            clean_response = clean_response[3:]
        if clean_response.endswith("```"):
            clean_response = clean_response[:-3]
            
        data = json.loads(clean_response.strip())
        final_intent = data.get("intent", "execute")
        needs_plot = data.get("needs_plot", False)
    except:
        final_intent = "execute"
        needs_plot = False
        
    return {"intent": final_intent, "needs_plot": needs_plot}

async def chat_node(state: AgentState):
    msg = state["messages"][-1].content
    response = await call_ollama(msg)
    return {
        "messages":[AIMessage(content=response)]
    }   
async def code_generator_node(state: AgentState):
    user_query = state["messages"][-1].content
    dataset_schema = state.get("dataset_schema", "No schema provided")
    filename = state.get("filename", "")
    retries = state.get("retries", 0)

    load_instruction = ""
    if filename:
        import os
        uploads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))
        filepath = os.path.join(uploads_dir, filename).replace('\\', '/')
        if filename.endswith(".csv"):
            load_instruction = f"To load the dataset, read it directly: df = pd.read_csv('{filepath}')"
        elif filename.endswith((".xls", ".xlsx")):
            load_instruction = f"To load the dataset, read it directly: df = pd.read_excel('{filepath}')"

    if state.get("needs_plot"):
        plot_rule = "2. The user has requested a visualization. You MUST create a plot and assign the Plotly Figure object to a global variable named fig."
    else:
        plot_rule = "2. The user has NOT requested a visualization. You are STRICTLY FORBIDDEN from creating any plots, graphs, or importing matplotlib/plotly. Do NOT create any figures."

    if state.get("sandbox_success") is False:
        retries += 1
        last_code = state.get("last_code", "")
        stderr = state.get("stderr", "")
        prompt = f"""
You are a Python data analyst.
The previous code execution failed. Fix the provided code based on the error.
Generate only executable Python code.
No markdown.
No explanations.

Dataset Schema & Information:
{dataset_schema}

{load_instruction}

Previous Code:
{last_code}

Error message:
{stderr}

User request:
{user_query}

CRITICAL RULES:
1. Always use the exact column names present in the dataset schema above.
{plot_rule}
"""
    else:
        prompt = f"""
You are a Python data analyst.
Generate only executable Python code.
No markdown.
No explanations.

Dataset Schema & Information:
{dataset_schema}

{load_instruction}

User request:
{user_query}

CRITICAL RULES:
1. Always use the exact column names present in the dataset schema above.
{plot_rule}
"""

    code = await call_ollama(prompt)
    code = clean_python_code(code)
    return {
        "last_code": code,
        "retries": retries
    }

async def execution_node(state: AgentState):
    result = sandbox.execute(state["last_code"])
    return {
        "sandbox_success":result["success"],
        "stdout":result["stdout"],
        "stderr":result["stderr"],
        "plotly_json":result["plotly_json"]
    }

async def response_node(state: AgentState):
    if state.get("sandbox_success"):
        content = state.get("stdout", "")
        if state.get("plotly_json"):
            content += ( "\nChart generated.")
    else:
        retries = state.get("retries", 0)
        content = f"Execution failed after {retries} attempt(s):\n" + state.get("stderr", "")

    return {
        "messages":[
            AIMessage(content=content)
        ],
        "plotly_json": state.get("plotly_json", "")
    }

async def respond_code_node(state: AgentState):
    code = state.get("last_code", "")
    content = f"Here is the generated code:\n```python\n{code}\n```"
    return {
        "messages": [AIMessage(content=content)]
    }
# -------------------------
# Routers
# -------------------------
def route_after_intent(state: AgentState):
    intent = state.get("intent", "execute")
    if intent == "chat":
        return "chat"
    return "generate_code"

def route_after_code_generation(state: AgentState):
    intent = state.get("intent", "execute")
    if intent == "code":
        return "respond_code"
    return "execute"

def execution_router(state: AgentState):
    if state.get("sandbox_success"):
        return "respond"
    else:
        if state.get("retries", 0) < 3:
            return "generate_code"
        else:
            return "respond"

# -------------------------
# Graph
# -------------------------
workflow = StateGraph(AgentState)
workflow.add_node("detect_intent", detect_intent_node)
workflow.add_node("chat", chat_node)
workflow.add_node("generate_code", code_generator_node)
workflow.add_node("execute", execution_node)
workflow.add_node("respond", response_node)
workflow.add_node("respond_code", respond_code_node)

workflow.set_entry_point("detect_intent")

workflow.add_conditional_edges(
    "detect_intent",
    route_after_intent,
    {
        "chat": "chat",
        "generate_code": "generate_code"
    }
)

workflow.add_edge("chat", END)

workflow.add_conditional_edges(
    "generate_code",
    route_after_code_generation,
    {
        "execute": "execute",
        "respond_code": "respond_code"
    }
)

workflow.add_conditional_edges(
    "execute",
    execution_router,
    {
        "generate_code": "generate_code",
        "respond": "respond"
    }
)

workflow.add_edge("respond", END)
workflow.add_edge("respond_code", END)

app_graph = workflow.compile()