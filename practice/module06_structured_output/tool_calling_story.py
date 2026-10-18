# Module 06: Structured output & tool calling
# HAVE YOU USED TOOL CALLING? WHAT BROKE, AND HOW DID YOU HANDLE IT?
#
# The robot helper now has a TV remote with two buttons:
#   [get_order_status]  and  [issue_refund]
# But here's the trick: the robot can't actually press them. It can only
# SAY "please press issue_refund for order A123, $40". YOUR CODE holds the
# remote and decides whether to press.
#
# Version 1 presses whatever the robot asks for.
# Version 2 checks first: real order? this customer's order? sensible amount?
# already done? If something's wrong, it tells the robot WHY (a structured
# error), so the robot can explain it to the customer instead of crashing.

ORDERS = {
    "A123": {"owner": "sam", "total": 40, "status": "shipped"},
    "B777": {"owner": "lee", "total": 250, "status": "processing"},
}
REFUND_LIMIT = 100  # bigger refunds need a human to approve
USER = "sam"        # the customer who is signed in and chatting


# VERSION 1: press whatever the robot asks for --------------------------------
def run_v1(call, done):
    args = call["args"]
    order = ORDERS[args["order_id"]]
    if call["tool"] == "get_order_status":
        return f"status: {order['status']}"
    return f"REFUNDED ${args['amount']}"


# VERSION 2: check, then press ----------------------------------------------------
def error(code, hint):
    """What goes back to the robot when we say no: not a crash, a clear reason."""
    return f"error={code} (hint: {hint})"


def run_v2(call, done):
    args = call.get("args", {})
    order = ORDERS.get(args.get("order_id"))
    if order is None:
        return error("order_not_found", "ask the customer to confirm the order ID")
    if order["owner"] != USER:
        return error("not_your_order", "only discuss the signed-in customer's orders")
    if call["tool"] == "get_order_status":
        return f"status: {order['status']}"
    amount = args.get("amount", 0)
    if amount > min(order["total"], REFUND_LIMIT):
        return error("needs_approval", "offer to pass this to a human agent")
    if call["id"] in done:
        return error("already_done", "tell the customer the refund is already on its way")
    done.add(call["id"])
    return f"REFUNDED ${amount}"


# WHAT THE ROBOT ASKED FOR (seven real situations) ----------------------------
CALLS = [
    ("normal status check",          {"id": "c1", "tool": "get_order_status", "args": {"order_id": "A123"}}),
    ("made-up order ID",             {"id": "c2", "tool": "get_order_status", "args": {"order_id": "A999"}}),
    ("someone else's order",         {"id": "c3", "tool": "get_order_status", "args": {"order_id": "B777"}}),
    ("refund more than they paid",   {"id": "c4", "tool": "issue_refund", "args": {"order_id": "A123", "amount": 400}}),
    ("normal refund",                {"id": "c5", "tool": "issue_refund", "args": {"order_id": "A123", "amount": 40}}),
    ("same refund again (retry)",    {"id": "c5", "tool": "issue_refund", "args": {"order_id": "A123", "amount": 40}}),
    ("tricked by text in a ticket",  {"id": "c7", "tool": "issue_refund", "args": {"order_id": "B777", "amount": 5000}}),
]


def run_all(runner):
    done, results, money = set(), [], 0
    for name, call in CALLS:
        try:
            result = runner(call, done)
        except Exception as e:
            result = f"💥 CRASH ({type(e).__name__})"
        if result.startswith("REFUNDED"):
            money += int(result.split("$")[1])
        results.append(result)
    return results, money


v1, money_v1 = run_all(run_v1)
v2, money_v2 = run_all(run_v2)

print("THE SAME TOOL CALLS, TWO VERSIONS OF YOUR CODE (signed in: sam)")
print(f"   {'what the robot asked for':<30}{'VERSION 1: just press it':<28}VERSION 2: check, then press")
for (name, _), r1, r2 in zip(CALLS, v1, v2):
    print(f"   {name:<30}{r1:<28}{r2}")
print()
print(f"   money refunded:  version 1 = ${money_v1:,}   version 2 = ${money_v2:,}  (the right amount is $40)")
print()

print("WHAT BROKE, AND HOW I HANDLED IT")
print("   1. A made-up order ID crashed the whole chat.")
print("      -> Check the order exists. Send back a clear error with a hint, so the")
print("         robot asks the customer to confirm the ID instead of the chat dying.")
print("   2. The robot showed sam the status of lee's order.")
print("      -> Check ownership in CODE. 'Only discuss their own orders' in the prompt is")
print("         just a request; the code check is a guarantee.")
print("   3. It refunded $400 on a $40 order, and $5,000 after reading a sneaky ticket.")
print("      -> Limits live in the tool code, not the prompt. Big refunds go to a human.")
print("   4. A retry refunded the same order twice.")
print("      -> Every call has an id. Seen it already? Don't press the button again.")
print()
print("MY ANSWER")
print("   In my project the model asks for a tool and my code decides whether to run it.")
print("   What broke: made-up IDs crashed the flow, it accessed another customer's order,")
print("   it asked for refunds that were too large, and a retry repeated a refund. I fixed")
print("   each with a check in the tool code (exists, owner, limit, already done) and")
print("   return a structured error with a hint, so the model recovers instead of crashing.")


# YOUR TURN
# 1. Change USER to "lee". Run it. Which rows change in version 2, and why?
# 2. Set REFUND_LIMIT = 500. Is the $400 refund allowed now? (Look at the order total!)
# 3. Add a call with "args": {"order_id": 123} (a number). What does each version do?
#
# Explain it in one sentence: ____
