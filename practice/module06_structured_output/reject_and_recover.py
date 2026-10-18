# Module 06: Structured output & tool calling
# WHAT DO YOU DO WHEN THE MODEL RETURNS MALFORMED JSON,
# OR CALLS A TOOL WITH THE WRONG ARGUMENTS?
#
# Think of a teacher marking homework:
#   1. CHECK it.                         (the guard from guarantee_schema.py)
#   2. Wrong? Hand it back and say EXACTLY what's wrong:
#      "You wrote 'High'. It must be 'high'. Fix only that."
#   3. Give ONE more try. Not ten: every try costs money and time.
#   4. Still wrong? STOP. Pass it to a grown-up (human review).
#      Never just guess the answer yourself, and never crash.
#
# The same 4 steps work for a bad form AND for a bad tool call.

import json

MAX_ATTEMPTS = 2  # one first try + one repair


def recover(model, check, task, fallback):
    """Ask, check, hand back with the exact problem, try again, then fall back.
    This function never crashes: every path ends with an answer or the fallback."""
    feedback = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        reply = model(task, feedback)
        result, problem = check(reply)
        print(f"      try {attempt}: {reply}")
        if problem is None:
            print(f"         ✅ passed")
            return result
        print(f"         ❌ {problem}")
        # The repair note: the model's own answer + the exact problem + "fix only that".
        feedback = f"Your answer was: {reply}\nProblem: {problem}\nFix only that and answer again."
    print(f"         🙋 {MAX_ATTEMPTS} tries used up -> fallback")
    return fallback


# A FAKE MODEL ---------------------------------------------------------------
# No API calls. For each task it has a first answer, and a second answer it
# gives once it has been told what was wrong.
SCRIPT = {
    # forms
    "my card was charged twice!!":   ['{"priority": "high", "topic": "billing"}'],
    "where is my parcel?":           ['{"priority": "High", "topic": "delivery"}',
                                      '{"priority": "high", "topic": "delivery"}'],
    "":                              ["There is no message to classify.",
                                      "Sorry, I still can't classify an empty message."],
    # tool calls
    "status of order A123?":         ['{"tool": "get_order_status", "args": {"order_id": 123}}',
                                      '{"tool": "get_order_status", "args": {"order_id": "A123"}}'],
    "status of order A999?":         ['{"tool": "get_order_status", "args": {"order_id": "A999"}}',
                                      '{"tool": "get_order_status", "args": {"order_id": "A999"}}'],
}


def fake_model(task, feedback):
    answers = SCRIPT[task]
    return answers[0] if feedback is None else answers[-1]


# CHECK 1: the form (same guard as guarantee_schema.py) -----------------------
SCHEMA = {"priority": ["low", "normal", "high"], "topic": ["billing", "delivery", "unknown"]}


def check_form(reply):
    try:
        form = json.loads(reply)
    except json.JSONDecodeError:
        return None, "that is not JSON. Reply with only the JSON object."
    for field, allowed in SCHEMA.items():
        if form.get(field) not in allowed:
            return None, f"{field} is {form.get(field)!r}. It must be one of {allowed}."
    return form, None


# CHECK 2: the tool call -------------------------------------------------------
ORDERS = {"A123": "shipped"}  # our pretend database


def check_tool_call(reply):
    try:
        call = json.loads(reply)
    except json.JSONDecodeError:
        return None, "that is not JSON."
    order_id = call.get("args", {}).get("order_id")       # .get: a missing field must not crash us
    if not isinstance(order_id, str):                     # wrong type -> the model can fix this
        return None, f"order_id must be text like 'A123', not {order_id!r}."
    if order_id not in ORDERS:                            # wrong fact -> only the customer can fix this
        return None, f"order {order_id} not found."
    return f"order {order_id} is {ORDERS[order_id]}", None


print("PART 1: BAD FORMS")
for message in ["my card was charged twice!!", "where is my parcel?", ""]:
    print(f"   message: {message!r}")
    answer = recover(fake_model, check_form, message, fallback="send to human review")
    print(f"      RESULT: {answer}\n")

print("PART 2: BAD TOOL CALLS")
for message in ["status of order A123?", "status of order A999?"]:
    print(f"   message: {message!r}")
    answer = recover(fake_model, check_tool_call, message,
                     fallback="ask the customer to double-check the order ID")
    print(f"      RESULT: {answer}\n")

print("WHAT JUST HAPPENED")
print("   5 messages, 0 crashes. Each one ended in a good answer or a safe fallback.")
print("   - 'High' and order_id=123 were fixed on try 2, because the note said exactly what was wrong.")
print("   - The empty message and order A999 can't be fixed by trying again, so after")
print("     2 tries they stopped and went to a person. No endless loop, no made-up answer.")
print()
print("MY ANSWER")
print("   I never pass model output straight to my code. I validate it. If it fails, I send")
print("   the model its own answer plus the exact error and ask it to fix only that. I allow")
print("   a small number of tries (usually 2), then fall back safely, e.g. human review,")
print("   and I log every fallback. Bad tool arguments get the same treatment: the error")
print("   goes back to the model instead of crashing the conversation.")


# YOUR TURN
# 1. Set MAX_ATTEMPTS = 1. Which messages now go to the fallback? What did you lose?
# 2. Set MAX_ATTEMPTS = 5. Does the empty message ever get fixed? What did the
#    extra tries cost you?
# 3. Add an order "A777": "processing" to ORDERS, and a message
#    "status of order A777?" to SCRIPT that works on the first try.
#
# Explain it in one sentence: ____
