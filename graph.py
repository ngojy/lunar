"""
Graph definition — wires all agent nodes together using LangGraph.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langgraph.graph import StateGraph, END

from state import AgentState
from agents import (
    orchestrator_router,
    orchestrator_assembler,
    researcher_node,
    executor_node,
    critic_node,
)
from memory import get_checkpointer


# Routing helper
def route_from_orchestrator(state: AgentState) -> str:
    """Map the orchestrator's decision to the next graph node."""
    decision = state.get("next_agent", "finish").lower()
    routes = {
        "researcher": "researcher",
        "executor": "executor",
        "critic": "critic",
        "finish": "assembler",
    }
    return routes.get(decision, "assembler")


# Graph builder
def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("orchestrator", orchestrator_router)
    graph.add_node("researcher", researcher_node)
    graph.add_node("executor", executor_node)
    graph.add_node("critic", critic_node)
    graph.add_node("assembler", orchestrator_assembler)

    # Entry point
    graph.set_entry_point("orchestrator")

    # Conditional routing from orchestrator
    graph.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        {
            "researcher": "researcher",
            "executor": "executor",
            "critic": "critic",
            "assembler": "assembler",
        },
    )

    # All specialists loop back to the orchestrator
    for node in ("researcher", "executor", "critic"):
        graph.add_edge(node, "orchestrator")

    # Assembler ends the run
    graph.add_edge("assembler", END)

    return graph

def compile_graph():
    """Compile the graph, attaching a checkpointer if configured."""
    graph = build_graph()
    checkpointer = get_checkpointer()
    return graph.compile(checkpointer=checkpointer)

# Singleton — import this in main.py
app = compile_graph()