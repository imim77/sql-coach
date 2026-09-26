import re

from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.db import SCHEMA_TEXT
from app.exercises import Exercise

LEAK = re.compile(r"```|\bselect\b", re.IGNORECASE)

COACH_RULES = """You are a SQL coach for a learner using PostgreSQL.
Reply in at most two short sentences.
Level 1: a concept nudge only.
Level 2: name the clause or join shape.
Level 3: name the technique without writing SQL.
Never write a SELECT statement, a code fence, or a corrected query.
Do not list the expected result rows."""


def coach_note(exercise: Exercise, sql: str, level: int, diff: str) -> dict:
    fallback = exercise.hints[level - 1]
    if not OPENAI_API_KEY:
        return _fallback(fallback, level)

    payload = (
        f"Exercise: {exercise.title}\n"
        f"Question: {exercise.prompt}\n"
        f"Level: {level}\n"
        f"Schema:\n{exercise.schema_text or SCHEMA_TEXT}\n\n"
        f"Learner SQL:\n{sql}\n\n"
        f"Check result: {diff}"
    )
    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY, timeout=30)
        response = client.responses.create(
            model=OPENAI_MODEL,
            instructions=COACH_RULES,
            reasoning={"effort": "none"},
            max_output_tokens=200,
            input=payload,
        )
        note = (response.output_text or "").strip()
    except Exception:
        return _fallback(fallback, level)

    if not note or LEAK.search(note):
        return _fallback(fallback, level)
    return {"note": note, "level": level, "source": "coach"}


def _fallback(note: str, level: int) -> dict:
    return {"note": note, "level": level, "source": "notes"}


ASK_RULES = """You are a SQL coach for a learner using PostgreSQL.
Reply in at most two short sentences.
Answer the student's question about their query.
Never write a SELECT statement, a code fence, or a corrected query.
Do not list the expected result rows."""

ASK_FALLBACK = (
    "Say what you want the result to include, and which table it comes from. "
    "I will not write the query."
)


def ask_coach(exercise: Exercise, sql: str, question: str) -> dict:
    text = question.strip()
    if not text:
        raise ValueError("Ask a question first.")
    if not OPENAI_API_KEY:
        return _ask_fallback()

    payload = (
        f"Exercise: {exercise.title}\n"
        f"Prompt: {exercise.prompt}\n"
        f"Schema:\n{exercise.schema_text or SCHEMA_TEXT}\n\n"
        f"Learner SQL:\n{sql}\n\n"
        f"Student question: {text}"
    )
    try:
        answer = _model_answer(ASK_RULES, payload)
    except Exception:
        return _ask_fallback()
    if not answer or LEAK.search(answer):
        return _ask_fallback()
    return {"answer": answer, "source": "coach"}


def _model_answer(instructions: str, payload: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY, timeout=30)
    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=instructions,
        reasoning={"effort": "none"},
        max_output_tokens=200,
        input=payload,
    )
    return (response.output_text or "").strip()


def _ask_fallback() -> dict:
    return {"answer": ASK_FALLBACK, "source": "notes"}
