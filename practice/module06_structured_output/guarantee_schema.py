# Module 06: Structured output & tool calling
# HOW DO YOU GUARANTEE AN LLM'S OUTPUT MATCHES A SCHEMA YOUR CODE DEPENDS ON?
#
# A robot cashier writes order slips for your kitchen. The kitchen only reads
# slips like {"priority": "high", "topic": "billing"}. You can:
#
#   WAY 1. ASK nicely ("write neat slips") and TRUST every slip.
#          Most slips are fine. A weird one crashes the kitchen, or worse,
#          gets cooked wrong and nobody notices.
#   WAY 2. CHECK every slip at the door. Weird slips are stopped before
#          they reach the kitchen. (parse + validate)
#   WAY 3. Give the robot a STAMP that can only print legal words. Weird
#          slips can't be written at all. (constrained decoding)
#
# The real answer is WAY 3 + WAY 2: the stamp makes bad shapes impossible,
# and the door check still catches the one thing a stamp can't fix (a slip
# torn off halfway because the robot ran out of paper = max_tokens).

import json

SCHEMA = {
    "priority": ["low", "normal", "high"],
    "topic": ["billing", "delivery", "unknown"],
}

# What a "Return only JSON" prompt gave back on five different calls.
REPLIES = [
    ("good",           '{"priority": "high", "topic": "billing"}'),
    ("prose wrapping", 'Sure! Here is the JSON: {"priority": "high", "topic": "billing"}'),
    ("missing comma",  '{"priority": "high" "topic": "billing"}'),
    ("wrong value",    '{"priority": "High", "topic": "billing"}'),
    ("cut off",        '{"priority": "high", "top'),
]


def kitchen(record):
    """The downstream code that DEPENDS on the shape.
    It has a 'safe' default for unknown priorities... which hides mistakes."""
    team = {"billing": "Billing team", "delivery": "Shipping team", "unknown": "Human review"}[record["topic"]]
    hours = {"low": 48, "normal": 24, "high": 4}.get(record["priority"], 48)
    return f"{team}, reply within {hours}h"


# WAY 1: trust it ----------------------------------------------------------
def trust(text):
    try:
        return kitchen(json.loads(text))
    except Exception as e:
        return f"CRASH ({type(e).__name__})"


# WAY 2: check it at the door ----------------------------------------------
def check(text):
    """Returns (record, None) if the slip is legal, or (None, reason) if not."""
    try:
        record = json.loads(text)                       # 1. does it parse?
    except json.JSONDecodeError as e:
        return None, f"not JSON: {e.msg}"
    for field, allowed in SCHEMA.items():               # 2. does it match the schema?
        if field not in record:
            return None, f"missing field '{field}'"
        if record[field] not in allowed:
            return None, f"{field}={record[field]!r} is not one of {allowed}"
    extra = set(record) - set(SCHEMA)
    if extra:
        return None, f"extra field(s) {extra}"
    return record, None


# WAY 3: the stamp (constrained decoding) ----------------------------------
# The model picks one value per field from its own preferences.
# The model's favourite priority word here is "High", which is NOT allowed.
MODEL_LIKES = {
    "priority": {"High": 0.5, "high": 0.3, "urgent": 0.2},
    "topic": {"billing": 0.9, "Billing": 0.1},
}


def generate(constrained, budget=2):
    """Write the slip field by field. `budget` = how many fields fit before
    the robot runs out of paper (like max_tokens)."""
    slip = {}
    for i, field in enumerate(SCHEMA):
        if i >= budget:
            return json.dumps(slip)[:-1] + ', "'          # torn off mid-slip
        menu = MODEL_LIKES[field]
        if constrained:
            menu = {word: p for word, p in menu.items() if word in SCHEMA[field]}  # THE MASK
        slip[field] = max(menu, key=menu.get)           # pick its favourite from the menu
    return json.dumps(slip)


print("WAY 1 vs WAY 2: the same five replies")
print(f"   {'reply':<16}{'WAY 1: trust it':<34}WAY 2: check it")
for name, text in REPLIES:
    record, reason = check(text)
    verdict = "accepted -> " + kitchen(record) if record else "REJECTED: " + reason
    print(f"   {name:<16}{trust(text):<34}{verdict}")
print()
print("   Look at 'wrong value': WAY 1 didn't crash. It quietly treated 'High' as")
print("   48h instead of 4h. That's the silent kind of failure: the worst kind.")
print()

print("WAY 3: the stamp")
print(f"   no stamp:          {generate(constrained=False)}")
print(f"   stamp:             {generate(constrained=True)}")
print(f"   stamp, tiny paper: {generate(constrained=True, budget=1)}")
record, reason = check(generate(constrained=True, budget=1))
print(f"   ...and WAY 2 on that torn slip: REJECTED: {reason}")
print()

print("MY ANSWER")
print("   A prompt only ASKS for the shape. To GUARANTEE it, I use structured output")
print("   (constrained decoding): the model can only pick tokens that fit the schema.")
print("   I still validate every reply, because a cut-off reply (max_tokens) or a")
print("   config change can still slip through, and I check stop_reason first.")


# YOUR TURN
# 1. Add "Billing" (capital B) to REPLIES. Which way catches it, and which way
#    crashes? Why is that a different failure from "High"?
# 2. In MODEL_LIKES, give "urgent" the biggest number. What does the stamp
#    pick now? Why can it never pick "urgent"?
# 3. In kitchen(), remove .get(..., 48) and use [record["priority"]] instead.
#    Run it again. Is a crash better or worse than a silent wrong answer?
#
# Explain it in one sentence: ____
