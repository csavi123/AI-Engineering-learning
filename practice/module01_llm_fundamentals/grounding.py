# WHY HALLUCINATION IS STRUCTURAL, NOT A BUG
#
# The model doesn't look facts up in a book. It picks the next word that
# SOUNDS most likely, from patterns it saw while learning.
#   - Common fact  -> "sounds right" and "is true" match.      france -> paris
#   - Rare fact    -> they split: it says the famous-sounding answer,
#                     fluently and confidently.                australia -> sydney (true: canberra)
#   - Unknown fact -> the spinner has no "I don't know" slice, so it STILL answers.
# It has a "sounds right" meter but NO "is true" meter. A prompt like
# "please be accurate" can't add facts or a truth meter.
# The fix is OUTSIDE the model: GROUNDING. Put the real facts on the
# whiteboard (context window) and answer only from them, or say "I don't know".

# What the toy model learned. Only very common facts got memorised.
memorised = {"france": "paris", "japan": "tokyo"}
# The most talked-about city for each country: what "sounds right".
famous_city = {"australia": "sydney"}
# The city it saw most often overall: its last-resort guess.
MOST_SEEN_CITY = "paris"


def toy_model(country, prompt=""):
    """Answer "what is the capital of ___?" from memory alone (closed book)."""
    # The model reads `prompt`, but it has no truth meter to use it with,
    # so "please be accurate" changes nothing below.
    if country in memorised:
        return memorised[country]
    if country in famous_city:
        return famous_city[country]  # sounds right, might be wrong
    return MOST_SEEN_CITY            # never says "I don't know"


def grounded_model(country, document):
    """Answer ONLY from the document on the whiteboard (open book)."""
    for sentence in document:
        if sentence.endswith(f"capital of {country}."):
            return sentence.split()[0]  # the first word is the city
    return "I don't know"


# The real facts we put on the whiteboard.
document = [
    "paris is the capital of france.",
    "canberra is the capital of australia.",
]

# Used only to mark answers right or wrong. None = the country doesn't exist.
truth = {"france": "paris", "australia": "canberra", "wakanda": None}


def mark(country, answer):
    if truth[country] is None:
        return "✅" if answer == "I don't know" else "❌"
    return "✅" if answer == truth[country] else "❌"


print(f"{'capital of':<12}{'plain model':<16}{'+ be accurate':<16}grounded (open book)")
for country in truth:
    plain = toy_model(country)
    polite = toy_model(country, prompt="please be accurate")
    grounded = grounded_model(country, document)
    print(f"{country:<12}"
          f"{plain + ' ' + mark(country, plain):<16}"
          f"{polite + ' ' + mark(country, polite):<16}"
          f"{grounded} {mark(country, grounded)}")


# YOUR TURN
# 1. Delete the australia line from `document`. What does the grounded model say now?
#    Is that better or worse than the plain model's answer?
# 2. Add "japan" to `truth` and a japan sentence to `document`. Run it again.
# 3. Why does the "+ be accurate" column never change?
#
# Explain it in one sentence: ____
