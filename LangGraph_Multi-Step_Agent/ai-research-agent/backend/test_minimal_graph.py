
# test_minimal_graph.py
from langgraph.graph import StateGraph, END
from typing import TypedDict

class State(TypedDict):
    value: str

def node_a(state: State):
    print("Node A")
    return {"value": "processed"}

def node_b(state: State):
    print("Node B")
    return {"value": state["value"] + " completed"}

# Build graph
builder = StateGraph(State)
builder.add_node("a", node_a)
builder.add_node("b", node_b)
builder.set_entry_point("a")  # Instead of START
builder.add_edge("a", "b")
builder.add_edge("b", END)

# Compile and run
graph = builder.compile()
result = graph.invoke({"value": "start"})
print(f"Result: {result}")