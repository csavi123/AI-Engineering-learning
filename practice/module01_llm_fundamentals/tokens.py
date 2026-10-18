# TOKENS vs WORDS
#
# The model doesn't read words. It reads TOKENS: chunks from a fixed box of
# LEGO bricks (its "vocabulary").
#   - A common word is usually ONE brick:          "pizza" -> [pizza]
#   - A rare or long word is built from SEVERAL:   "unbelievably" -> [un][believ][ab][ly]
#   - If no bigger brick fits, it falls back to tiny one-letter bricks.
# Why it matters: you PAY per brick, and the model's memory (context window)
# is measured in bricks, not words.

# The box of bricks. A real model has ~100,000 of these; ours has a handful.
VOCAB = {"the", "cat", "sat", "good", "pizza", "year", "un", "believ", "ab", "ly","test","123"}


def tokenize(word):
    """Chop one word into bricks, always grabbing the LONGEST brick that fits."""
    pieces = []
    start = 0
    while start < len(word):
        # Try the longest possible chunk first, then shorter and shorter.
        for end in range(len(word), start, -1):
            chunk = word[start:end]
            if chunk in VOCAB or len(chunk) == 1:  # a single letter always fits
                pieces.append(chunk)
                start = end
                break
    return pieces


def count(sentence):
    """Return (number of words, number of tokens, list of tokens)."""
    words = sentence.split()
    tokens = []
    for word in words:
        tokens += tokenize(word)
    return len(words), len(tokens), tokens


# Only print the table when this file is run directly
# (not when another file borrows `count` with `from tokens import count`).
if __name__ == "__main__":
    sentences = [
        "the cat sat",              # common words
        "unbelievably good pizza",  # one long word
        "the year 2026",            # a number
        "quokka",                   # a rare word the box doesn't know
        "test123 is random"
    ]

    print(f"{'sentence':<26}{'words':>6}{'tokens':>8}   pieces")
    for s in sentences:
        n_words, n_tokens, tokens = count(s)
        pieces = "".join(f"[{t}]" for t in tokens)
        print(f"{s:<26}{n_words:>6}{n_tokens:>8}   {pieces}")


# YOUR TURN
# 1. Add your own sentence (or a made-up word) to `sentences`.
#    Guess its token count BEFORE you run the file.
# 2. Add "unbelievably" to VOCAB and run again. What happened to its count?
#    (That's what happens to words a real model sees a lot: they get their own brick.)
#
# Explain it in one sentence: ____
