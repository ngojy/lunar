"""
Graph definition for Phase 2-3 hierarchical pipeline with selective critique.
Implements: User → Session → Router → Planning (optional) → Parallel Capabilities → Synthesizer → Critique (optional) → Response
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langgraph.graph import StateGraph, END

from state import AgentState
from memory_integration import load_session_context
from agents import (
    router_node,
    planning_node,
    retrieval_node,
    tools_registry_node,
    research_specialist_node,
    coding_specialist_node,
    synthesizer_node,
    critic_node,
)
from agents.critic import should_critique
from memory import get_checkpointer


def route_after_router(state: AgentState) -> str:
    """Route after router: to planning if needed, else to parallel execution."""
    if state.get("needs_reasoning", False):
        return "planning"
    else:
        return "retrieve_or_skip"


def route_retrieve(state: AgentState) -> str:
    """Conditionally run retrieval node."""
    if state.get("needs_retrieval", False):
        return "retrieval"
    else:
        return "tools_or_skip"


def route_tools(state: AgentState) -> str:
    """Conditionally run tools registry node."""
    if state.get("needs_tools", False):
        return "tools_registry"
    else:
        return "route_specialists"


def route_specialists(state: AgentState) -> str:
    """Route to appropriate specialist(s)."""
    specialist_types = state.get("specialist_types", [])
    
    # If we have specialists, route to first one; they'll update specialist_results
    if "research" in specialist_types:
        return "research_specialist"
    elif "coding" in specialist_types:
        return "coding_specialist"
    else:
        return "post_specialists"


def route_second_specialist(state: AgentState) -> str:
    """After first specialist, check if second specialist is needed."""
    specialist_types = state.get("specialist_types", [])
    specialist_results = state.get("specialist_results", {})
    
    # Check if we need additional specialists
    if "research" in specialist_types and "research" not in specialist_results:
        return "research_specialist"
    elif "coding" in specialist_types and "coding" not in specialist_results:
        return "coding_specialist"
    else:
        return "post_specialists"


def route_after_parallel(state: AgentState) -> str:
    """Route after parallel phase: synthesize the final response by default."""
    return "synthesizer"


def check_critique_route(state: AgentState) -> str:
    """Determine if critique should run."""
    if should_critique(state):
        return "critic"
    else:
        return "finish"


def finish_node(state: AgentState) -> AgentState:
    """
    Finish node: prepare final response.
    If synthesis was done, use that. Otherwise use specialist output or router decision.
    """
    if state.get("synthesis_performed"):
        final_response = state.get("final_response", "No response generated")
    else:
        # Use specialist results if available
        specialist_results = state.get("specialist_results", {})
        if specialist_results:
            # Combine all specialist outputs
            final_response = "\n\n".join(
                f"{k.upper()}:\n{v}"
                for k, v in specialist_results.items()
            )
        else:
            final_response = "Task completed without specialist execution"
    
    return {
        **state,
        "final_response": final_response,
    }


def pass_through(state: AgentState) -> AgentState:
    """No-op routing node used to satisfy LangGraph topology."""
    return state


# Graph builder

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    
    # Sequential nodes
    graph.add_node("session_context", load_session_context)
    graph.add_node("router", router_node)
    graph.add_node("planning", planning_node)
    graph.add_node("retrieve_or_skip", pass_through)
    graph.add_node("tools_or_skip", pass_through)
    graph.add_node("route_specialists", pass_through)
    graph.add_node("check_critique", pass_through)
    
    # Parallel execution nodes (run conditionally)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("tools_registry", tools_registry_node)
    graph.add_node("research_specialist", research_specialist_node)
    graph.add_node("coding_specialist", coding_specialist_node)
    
    # Synthesis and finish
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("critic", critic_node)
    graph.add_node("finish", finish_node)
    
    # Entry point
    graph.set_entry_point("session_context")
    
    # Sequential: session_context → router
    graph.add_edge("session_context", "router")
    
    # Router → planning or parallel
    graph.add_conditional_edges(
        "router",
        route_after_router,
        {
            "planning": "planning",
            "retrieve_or_skip": "retrieve_or_skip",
        },
    )
    
    # Planning → parallel
    graph.add_edge("planning", "retrieve_or_skip")
    
    # Parallel execution: Retrieval (conditional)
    graph.add_conditional_edges(
        "retrieve_or_skip",
        route_retrieve,
        {
            "retrieval": "retrieval",
            "tools_or_skip": "tools_or_skip",
        },
    )
    
    # Parallel execution: Tools (conditional)
    graph.add_conditional_edges(
        "tools_or_skip",
        route_tools,
        {
            "tools_registry": "tools_registry",
            "route_specialists": "route_specialists",
        },
    )
    
    # Retrieval → route specialists
    graph.add_edge("retrieval", "route_specialists")
    
    # Tools → route specialists
    graph.add_edge("tools_registry", "route_specialists")
    
    # Route to specialists (conditional)
    graph.add_conditional_edges(
        "route_specialists",
        route_specialists,
        {
            "research_specialist": "research_specialist",
            "coding_specialist": "coding_specialist",
            "post_specialists": "post_specialists",
        },
    )
    
    # Check for second specialist (conditional)
    graph.add_conditional_edges(
        "research_specialist",
        route_second_specialist,
        {
            "research_specialist": "research_specialist",
            "coding_specialist": "coding_specialist",
            "post_specialists": "post_specialists",
        },
    )
    
    # Check for second specialist after coding
    graph.add_conditional_edges(
        "coding_specialist",
        route_second_specialist,
        {
            "research_specialist": "research_specialist",
            "coding_specialist": "coding_specialist",
            "post_specialists": "post_specialists",
        },
    )
    
    # Fake node for converging paths
    graph.add_node("post_specialists", pass_through)
    
    # Post-specialists: Check if synthesis needed
    graph.add_conditional_edges(
        "post_specialists",
        route_after_parallel,
        {
            "synthesizer": "synthesizer",
        },
    )
    
    # Synthesizer → check critique
    graph.add_edge("synthesizer", "check_critique")
    
    # Check critique conditional routing
    graph.add_conditional_edges(
        "check_critique",
        check_critique_route,
        {
            "critic": "critic",
            "finish": "finish",
        },
    )
    
    # Critic → finish
    graph.add_edge("critic", "finish")
    
    # Finish → END
    graph.add_edge("finish", END)
    
    return graph


def compile_graph():
    """Compile the graph with checkpointer."""
    graph = build_graph()
    checkpointer = get_checkpointer()
    return graph.compile(checkpointer=checkpointer)


# Singleton
app = compile_graph()


