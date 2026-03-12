"""Claude AI service — natural language Q&A over document chunks.

Usage:
    from app.services.claude_service import ask

    answer = await ask(
        question="What powers does MCFD have to remove a child?",
        chunks=[
            {"id": 1, "citation": "CFCSA s.30", "text": "...", "source": "legislation"},
            {"id": 2, "citation": "2024 BCSC 101", "text": "...", "source": "bccourts"},
        ]
    )
"""

import os
import anthropic

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")
        _client = anthropic.AsyncAnthropic(api_key=api_key)
    return _client


SYSTEM_PROMPT = """\
You are a legal research assistant for The MCFD Files, a database of BC court decisions, \
legislation, and reports relating to the Ministry of Children and Family Development (MCFD).

Answer the user's question using ONLY the documents provided. \
Cite every factual claim with [Source: <citation>] immediately after the claim. \
If multiple documents support the same claim, include all relevant citations. \
If the provided documents do not contain enough information to answer the question, \
say so clearly — do not speculate or use outside knowledge. \
Be concise and precise. Use plain language.\
"""

PERSONAL_SYSTEM_PROMPT = """\
You are analyzing documents from C.L.'s personal legal case files. \
These are BC child protection proceedings PC 19700, PC 19709, SC 64242, SC 064851.

Answer precisely and cite the exact document name and page range for every claim. \
Use [Source: citation] immediately after each factual statement. \
Do not speculate. If the document does not contain the answer, say so.\
"""

_PROMPTS = {
    'personal': PERSONAL_SYSTEM_PROMPT,
    'public': SYSTEM_PROMPT,
}


def _build_context(chunks: list[dict]) -> str:
    """Format document chunks into a numbered context block."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        citation = chunk.get("citation") or chunk.get("id") or f"doc-{i}"
        source = chunk.get("source", "")
        text = chunk.get("text") or chunk.get("full_text") or chunk.get("snippet") or ""
        parts.append(
            f"[Document {i}]\n"
            f"Citation: {citation}\n"
            f"Source type: {source}\n"
            f"Text:\n{text.strip()}\n"
        )
    return "\n---\n".join(parts)


async def ask_stream(question: str, chunks: list[dict], context_mode: str = 'public'):
    """Stream Claude's answer token-by-token.

    Yields:
        ("token", text_fragment)  for each streamed token
        ("done", full_text)       when stream ends with complete answer
    """
    if not chunks:
        yield ("done", "No relevant documents were found to answer your question.")
        return

    context = _build_context(chunks)
    user_message = f"Documents:\n\n{context}\n\nQuestion: {question}"
    system_prompt = _PROMPTS.get(context_mode, SYSTEM_PROMPT)

    client = _get_client()
    full_text = ""
    async with client.messages.stream(
        model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"),
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        async for text in stream.text_stream:
            full_text += text
            yield ("token", text)

    yield ("done", full_text)


async def ask(question: str, chunks: list[dict], context_mode: str = 'public') -> str:
    """Ask Claude a question grounded in the provided document chunks.

    Args:
        question: The user's natural-language question.
        chunks:   List of dicts, each with keys: id, citation, text (or full_text/snippet), source.

    Returns:
        Answer string with inline [Source: citation] references.
    """
    if not chunks:
        return "No relevant documents were found to answer your question."

    context = _build_context(chunks)
    user_message = f"Documents:\n\n{context}\n\nQuestion: {question}"
    system_prompt = _PROMPTS.get(context_mode, SYSTEM_PROMPT)

    client = _get_client()
    response = await client.messages.create(
        model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"),
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text
