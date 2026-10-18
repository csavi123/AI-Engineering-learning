# THE CONTEXT WINDOW IS THE MODEL'S ENTIRE WORLD
#
# The model has NO memory. Every time you send a message, the app copies the
# WHOLE chat onto a WHITEBOARD, and the model reads only that board.
#   - The board fits a fixed number of bricks (tokens), its "context window".
#   - When the board is full, the OLDEST messages get wiped off to make room.
#   - Anything not on the board doesn't exist for the model. It can't
#     "remember" what was wiped.

from tokens import count  # the brick counter we built in tokens.py

# The chat so far, oldest first. The important fact is said FIRST.
chat = [
    "my name is sam",
    "the cat sat",
    "good pizza",
    "the year 2026",
]


def fit_on_board(chat, board_size):
    """Keep the NEWEST messages that fit on the board; wipe the rest."""
    board = []
    used = 0
    for message in reversed(chat):  # start from the newest message
        size = count(message)[1]    # how many bricks this message needs
        if used + size > board_size:
            break                   # no room: this and all older messages are wiped
        board.insert(0, message)    # put it back in its original order
        used += size
    return board


def toy_model(board):
    """Answer "what is my name?" by looking ONLY at the board."""
    for message in board:
        if message.startswith("my name is "):
            return "Your name is " + message[len("my name is "):] + "."
    return "I don't know your name."


print("The chat (bricks per message):")
for message in chat:
    print(f"  {count(message)[1]:>2}  {message}")
print()

for name, board_size in [("BIG", 30), ("SMALL", 12)]:
    board = fit_on_board(chat, board_size)
    on_board = " ".join(f"[{m}]" for m in board)
    print(f"{name} board ({board_size} bricks): {on_board}")
    print(f"  model says: {toy_model(board)}")
    print()


# YOUR TURN
# 1. Make the BIG board smaller one step at a time (30, 25, 22, 21...).
#    At which size does the name vanish? (Hint: add up the bricks above.)
# 2. Move "my name is sam" to the END of the chat. Does the SMALL board
#    remember it now? Why?
#
# Explain it in one sentence: ____
