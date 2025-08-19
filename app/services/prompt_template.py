from typing import List, Dict
from pathlib import Path
from jinja2 import Template


def load_prompt_template(name: str) -> Template:
    """
    Load a Jinja2 template from the prompts directory.

    Args:
        name (str): The base name of the prompt file (without extension).

    Returns:
        Template: A compiled Jinja2 template ready for rendering.
    """
    prompt_path = Path("app/prompts") / f"{name}.txt"
    text = prompt_path.read_text(encoding="utf-8")
    return Template(text)


def build_chat_prompt(
    video_title: str,
    context: str,
    session_history: List[Dict[str, str]],
    user_query: str,
) -> str:
    """
    Build a RAG (Retrieval-Augmented Generation) prompt for the LLM with
    enhanced, teacher-style conversational instructions.

    Args:
        video_title (str): The title of the video being discussed.
        context (str): Relevant transcript or extracted notes to ground responses.
        session_history (List[Dict[str, str]]): Chat history with keys "user" and "bot".
        user_query (str): The current user question to be answered.

    Returns:
        str: A formatted prompt string ready for sending to the LLM.
    """
    formatted_history = format_chat_history(session_history)
    template = load_prompt_template("tutor_prompt")

    return template.render(
        video_title=video_title,
        context=context or "No relevant context available.",
        formatted_history=formatted_history,
        user_query=user_query,
    )


def format_chat_history(history: List[Dict[str, str]]) -> str:
    """
    Convert a chat history list into a formatted string for prompt injection.

    Args:
        history (List[Dict[str, str]]): A list of conversation turns where each dict
            contains:
                - "user" (str): The user’s message.
                - "bot" (str): The assistant’s response.

    Returns:
        str: A formatted multi-line string representing the conversation history.
    """
    if not history:
        return "No previous messages."

    lines = []
    for i, turn in enumerate(history, 1):
        user_msg = turn.get("user", "")
        bot_msg = turn.get("bot", "")
        lines.append(f"{i}. User: {user_msg}\n   Assistant: {bot_msg}")

    return "\n".join(lines)
