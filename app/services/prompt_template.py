from typing import List, Dict


def build_chat_prompt(video_title: str, context: str, session_history: List[Dict[str, str]], user_query: str) -> str:
    """
    Build a clear RAG prompt for the LLM. Keep this function pure and easy to extend.
    """
    formatted_history = format_chat_history(session_history)

    return f"""
You are an expert, concise, and helpful tutoring assistant.

Video title: "{video_title}"

Relevant context (from the video's transcript / extracted notes):
---
{context or 'No relevant context available.'}
---

Conversation history:
{formatted_history}

User's current question:
\"\"\"{user_query}\"\"\"

Instructions for the assistant:
- Prefer facts from the "Relevant context" above. If the answer is not present, say you don't know.
- If you must infer, label it as an inference.
- Keep responses clear and step-by-step when appropriate.
- If the user asks for follow-up steps, give 2–4 concise steps.

Answer now:
"""


def format_chat_history(history: List[Dict[str, str]]) -> str:
    if not history:
        return "No previous messages."
    lines = []
    for i, turn in enumerate(history, 1):
        u = turn.get("user", "")
        b = turn.get("bot", "")
        lines.append(f"{i}. User: {u}\n   Assistant: {b}")
    return "\n".join(lines)
