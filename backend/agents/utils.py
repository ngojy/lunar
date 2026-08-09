"""
Shared utility functions for agents.
"""

import sys
import time
import threading


def spinner(label: str, stop_event: threading.Event, start: float) -> None:
    """
    Display an animated spinner with elapsed time during long operations.
    
    Args:
        label: Text label to display
        stop_event: threading.Event to signal when to stop the spinner
        start: Start time (time.time()) for elapsed calculation
    """
    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    i = 0
    while not stop_event.is_set():
        elapsed = time.time() - start
        sys.stdout.write(f"\r  {frames[i % len(frames)]}  {label}  {elapsed:.1f}s ")
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1


def timed_invoke(llm, messages, label: str, show_completion: bool = False):
    """
    Invoke an LLM with a spinner showing elapsed time.
    
    Args:
        llm: LangChain ChatOllama instance
        messages: Messages to pass to the LLM
        label: Label for the spinner
        show_completion: If True, show completion time after spinner stops
        
    Returns:
        The result from llm.invoke()
    """
    stop = threading.Event()
    start = time.time()
    t = threading.Thread(target=spinner, args=(label, stop, start), daemon=True)
    t.start()
    try:
        result = llm.invoke(messages)
    finally:
        stop.set()
        t.join()
        if show_completion:
            elapsed = time.time() - start
            sys.stdout.write(f"\r  ✓  {label}  {elapsed:.2f}s\n")
            sys.stdout.flush()
    return result
