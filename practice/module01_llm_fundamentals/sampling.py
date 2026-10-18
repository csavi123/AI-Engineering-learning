# WHY OUTPUT IS NON-DETERMINISTIC
#
# The model doesn't "know" the next word. For every possible next brick it
# has a CHANCE, like:  pizza 60%, pasta 30%, salad 10%.
# Then it spins a WEIGHTED SPINNER: a big slice for pizza, a small one for salad.
#   - Usually it lands on pizza, but sometimes on pasta or salad.
#   - Same question, different spin, different answer.
# So the randomness is a dice roll ON PURPOSE, not a broken machine.
# TEMPERATURE 0 means "don't spin, always take the biggest slice",
# so you get ALMOST always the same answer. Not always: the computer's
# decimal math wobbles a tiny bit between calls, and when two words are
# nearly tied, that wobble can flip which slice is biggest (see the last block).

import random

# The model's chances for the next word after "for dinner i want ..."
chances = {"pizza": 0.6, "pasta": 0.3, "salad": 0.1}

TRIES = 100  # how many times we ask the same question


def pick_next(chances, temperature):
    """Pick the next word: take the biggest slice (temperature 0) or spin."""
    if temperature == 0:
        return max(chances, key=chances.get)  # no spin: the most likely word
    words = list(chances)
    weights = list(chances.values())
    return random.choices(words, weights)[0]  # spin the weighted spinner


def tally(answers):
    """Count how often each word came up, e.g. 'pizza 7, pasta 2, salad 1'."""
    return ", ".join(f"{w} {answers.count(w)}" for w in chances if w in answers)


shown = ", ".join(f"{w} {int(p * 100)}%" for w, p in chances.items())
print(f'Question: "for dinner i want ..."   chances: {shown}')
print()

for label, temperature in [("SPIN (normal)", 1), ("TEMPERATURE 0", 0)]:
    answers = [pick_next(chances, temperature) for _ in range(TRIES)]
    if TRIES <= 20:  # only print every answer when the list is short
        print(f"{label}, {TRIES} tries:  {' '.join(answers)}")
    else:
        print(f"{label}, {TRIES} tries:")
    print(f"  tally: {tally(answers)}")
    print()


# NEAR TIE: temperature 0, but pizza and pasta are almost equal.
near_tie = {"pizza": 0.501, "pasta": 0.499}
WOBBLE = 0.002  # tiny rounding noise, like a real GPU's decimal math


def wobbly(chances):
    """Nudge every chance up or down by a tiny random amount."""
    return {w: p + random.uniform(-WOBBLE, WOBBLE) for w, p in chances.items()}


answers = [pick_next(wobbly(near_tie), 0) for _ in range(TRIES)]
print(f"TEMPERATURE 0, NEAR TIE (pizza 50.1%, pasta 49.9%), {TRIES} tries:")
if TRIES <= 20:
    print(f"  {' '.join(answers)}")
print(f"  tally: {tally(answers)}")


# YOUR TURN
# 1. Run the file 3 times. Which line changes and which stays the same?
# 2. Change TRIES from 10 to 1000. Does the SPIN tally get close to 600 / 300 / 100?
# 3. Make the chances equal (0.34, 0.33, 0.33). Now how predictable is it?
# 4. In near_tie, widen the gap (pizza 0.6, pasta 0.4). Do the flips stop? Why?
#
# Explain it in one sentence: ____
