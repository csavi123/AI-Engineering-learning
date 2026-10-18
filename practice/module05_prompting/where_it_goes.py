# SYSTEM PROMPT vs CONTEXT WINDOW vs TOOL CALL: HOW DO YOU DECIDE?
#
# Think of your SCHOOL BAG:
#   - Timetable: same every day, needed every day
#       -> always in the bag                    = SYSTEM PROMPT
#   - Today's homework: different each day, you know in the morning you need it
#       -> packed that morning                  = CONTEXT WINDOW
#   - Library book: needed only sometimes, or it keeps changing
#       -> fetched only when you need it        = TOOL CALL
#
# Just two questions decide it:
#   1. Does it change?               (never / each request / live)
#   2. Is it needed on every call?   (yes / no)


def decide(changes, needed_every_time):
    # Keeps changing, even mid-conversation? Fetch it fresh when needed.
    if changes == "live":
        return "TOOL CALL"
    # Only needed sometimes? Don't pay for it on every call; fetch it when needed.
    if not needed_every_time:
        return "TOOL CALL"
    # Needed every time and never changes? Put it in once, at the top.
    if changes == "never":
        return "SYSTEM PROMPT"
    # Needed every time but different for each request.
    return "CONTEXT WINDOW"


# (item, does it change?, needed on every call?)
items = [
    ("Reply with one label: bug, question or billing", "never", True),
    ("Be polite and short", "never", True),
    ("The customer's message", "each request", True),
    ("The last 3 messages of this chat", "each request", True),
    ("This customer's order status", "live", False),
    ("Today's exchange rate", "live", False),
    ("The 40-page refund policy", "never", False),  # the tricky one
]

print(f"{'item':<50}{'changes':<14}{'every time?':<13}goes in")
for item, changes, needed in items:
    answer = decide(changes, needed)
    print(f"{item:<50}{changes:<14}{'yes' if needed else 'no':<13}{answer}")


# YOUR TURN
# 1. Add ("The customer's name", ?, ?) to items. Guess where it goes BEFORE running.
# 2. Change the refund policy to needed_every_time=True. Where does it go now?
#    Why might that be expensive? (Hint: 40 pages of tokens on EVERY call.)
#
# Explain it in one sentence: ____
