def summarize_text(text: str) -> dict:
    return {"summary": (text[:120] + "...") if len(text) > 120 else text}
