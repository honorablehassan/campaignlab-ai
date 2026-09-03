def bullet_block(items, empty_text="- None identified."):
    if not items:
        return empty_text
    return "\n".join(f"- {item}" for item in items)
