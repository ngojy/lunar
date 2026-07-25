"""
Entry point for the multi-agent system.
Usage:
    ~~                              # interactive prompt
    python main.py "What is LangGraph?"         # one-shot from CLI arg
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uuid
from pprint import pformat
from config import config
from graph import app

def run(task: str, verbose: bool = True) -> str:
    """
    Run the multi-agent system on a task and return the final answer.

    Args:
        task:    The user's request / question.
        verbose: If True, print each agent's messages as they stream in.

    Returns:
        The assembled final answer string.
    """
    config.validate()

    initial_state = {
        "task": task,
        "messages": [{"role": "user", "content": task}],
        "next_agent": "",
        "research_results": [],
        "execution_results": [],
        "critique": "",
        "final_answer": "",
        "iteration": 0,
        "metadata": {},
    }

    # thread_id scopes the checkpointer (one conversation = one thread)
    run_config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    if verbose:
        print(f"\n{'='*60}")
        print(f"  Task: {task}")
        print(f"{'='*60}\n")

    final_state = None

    for step in app.stream(initial_state, config=run_config):
        node_name, node_state = next(iter(step.items()))
        final_state = node_state

        if verbose:
            msgs = node_state.get("messages", [])
            for msg in msgs:
                role = msg.get("role", node_name)
                content = msg.get("content", "")
                print(f"[{role.upper()}] {content}")

    answer = (final_state or {}).get("final_answer", "No answer produced.")

    if verbose:
        print(f"\n{'='*60}")
        print("  FINAL ANSWER")
        print(f"{'='*60}")
        print(answer)
        print()

    return answer


# CLI
if __name__ == "__main__":
    if len(sys.argv) > 1:
        task_input = " ".join(sys.argv[1:])
    else:
        task_input = input("Enter your task: ").strip()
        if not task_input:
            print("No task provided. Exiting.")
            sys.exit(0)

    run(task_input)