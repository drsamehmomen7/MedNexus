"""Small, model-independent guards for runaway MedGemma generation."""

MAX_NEW_TOKENS = 2000
LIMIT_CODE = "GENERATION_REPETITION_LIMIT"


def repeated_token_block(tokens):
    """Detect three identical consecutive token blocks at the generated tail."""
    for size in range(8, min(64, len(tokens) // 3) + 1):
        if tokens[-size:] == tokens[-2 * size:-size] == tokens[-3 * size:-2 * size]:
            return True
    return False


def repeated_text_block(raw):
    """Catch obvious repeated lines or short line blocks in decoded output."""
    lines = [" ".join(line.casefold().split()) for line in str(raw or "").splitlines() if line.strip()]
    for size in range(1, min(4, len(lines) // 3) + 1):
        for end in range(3 * size, len(lines) + 1):
            block = lines[end - size:end]
            if sum(map(len, block)) >= 24 and block == lines[end - 2 * size:end - size] == lines[end - 3 * size:end - 2 * size]:
                return True
    return False
