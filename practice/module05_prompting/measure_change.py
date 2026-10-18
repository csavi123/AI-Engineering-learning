# DID THE PROMPT CHANGE REALLY HELP, OR DOES IT JUST FEEL BETTER?
#
# A taste test, not one spoonful:
#   1. FEELS BETTER: you check only the messages you were annoyed about.  (can fool you)
#   2. MEASURED:     both versions on the SAME labelled messages, every class scored.
#   3. NOISE:        run it again. If the score wobbles, small differences mean nothing.

import random

LABELS = ["bug", "question", "billing"]

# The test set: messages with the RIGHT answer. Same set for every version.
test_set = [
    ("the app crashes when I open settings", "bug"),
    ("why does the app crash when I upload?", "bug"),
    ("the save button is broken", "bug"),
    ("how do I change my password?", "question"),
    ("what does the error icon mean?", "question"),
    ("how do I read the error codes?", "question"),
    ("I was charged twice", "billing"),
    ("please send my invoice", "billing"),
    ("my payment page shows an error", "billing"),
]


def prompt_v1(msg):
    """Old prompt."""
    if "charge" in msg or "invoice" in msg or "payment" in msg:
        return "billing"
    if "?" in msg:
        return "question"
    return "bug"


def prompt_v2(msg):
    """New prompt, one change: anything with 'crash' or 'error' is a bug."""
    if "crash" in msg or "error" in msg:
        return "bug"
    return prompt_v1(msg)


def score(prompt):
    """Count right answers for each class."""
    right = {"bug": 0, "question": 0, "billing": 0}
    for msg, label in test_set:
        if prompt(msg) == label:
            right[label] += 1
    return right


# 1. FEELS BETTER: you try the 2 messages that annoyed you.
print("1) FEELS BETTER")
for msg, label in test_set[:2]:
    print(f"   {msg:<40} v1: {prompt_v1(msg):<9} v2: {prompt_v2(msg):<9} right: {label}")
print("   v2 looks perfect!")
print()

# 2. MEASURED: every message, every class.
print("2) MEASURED (right answers out of 3 per class)")
for name, prompt in [("v1", prompt_v1), ("v2", prompt_v2)]:
    right = score(prompt)
    total = sum(right.values())
    print(f"   {name}:  bug {right['bug']}/3   question {right['question']}/3   "
          f"billing {right['billing']}/3   TOTAL {total}/9")
print("   v2 fixed bugs but broke questions and billing. It's WORSE overall.")
print()


# 3. NOISE: a real model is a spinner, so ~10% of answers come out random.
def noisy(prompt, msg):
    if random.random() < 0.10:
        return random.choice(LABELS)
    return prompt(msg)


print("3) NOISE: the same v1, run 3 times")
for run in range(3):
    total = sum(noisy(prompt_v1, msg) == label for msg, label in test_set)
    print(f"   run {run + 1}: {total}/9")
print("   Same prompt, different scores. A difference smaller than this wobble isn't real.")


# YOUR TURN
# 1. Write prompt_v3 that fixes bugs WITHOUT breaking the other classes
#    (hint: check billing first; "how"/"what" questions about errors aren't bugs).
#    Add ("v3", prompt_v3) to the list in part 2. Did every class stay the same or improve?
# 2. Run the file 3 times. Which part changes, and which never does? Why?
#
# Explain it in one sentence: ____
