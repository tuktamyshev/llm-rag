def clean_text(raw_text: str) -> str:
    """
    Stub cleaning stage.
    Keeps behaviour deterministic and easy to replace later.
    """
    lines = [line.strip() for line in raw_text.splitlines()]
    compact = " ".join(part for part in lines if part)
    return " ".join(compact.split())
