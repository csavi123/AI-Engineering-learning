"""Registry of every demo, so lesson content (YAML) can refer to demos by id.

Each demo is a function that takes the app config and draws itself.
"free" demos make no API calls; "live" demos call Claude only when you click
Run, and save the result so viewing it later is free.
"""
from typing import Any, Callable, Dict, NamedTuple


class Demo(NamedTuple):
    title: str
    kind: str  # "free" or "live"
    fn: Callable[[Dict[str, Any]], None]


def _registry() -> Dict[str, Demo]:
    # Imported inside a function so a broken demo file can't stop the whole
    # app from loading; the error shows up only where that demo is used.
    from demos.ch01 import (
        context, generation, knowledge, long_context, memory, sampling, sensitivity,
        simulators, tokens, transformer,
    )
    from demos.ch05 import lab, lessons
    from demos.ch06 import lessons as ch06

    return {
        "loop_stepper": Demo("Step through the generation loop", "free", simulators.loop_stepper),
        "token_by_token": Demo("Run the loop with Claude, one token at a time", "live", generation.token_by_token),
        "streaming": Demo("Watch an answer arrive (streaming)", "live", generation.streaming),
        "input_vs_output": Demo("Reading is parallel, writing is sequential", "live", generation.input_vs_output),
        "compounding": Demo("Plant a wrong premise and watch it grow", "live", generation.compounding),
        "opening_word": Demo("One opening word steers the whole shape", "live", generation.opening_word),
        "one_token_sampling": Demo("Sample one next token many times", "live", sampling.one_token_sampling),
        "made_up_fact": Demo("Ask for a fact that doesn't exist", "live", knowledge.made_up_fact),
        "code_word": Demo("Two calls share nothing", "live", memory.code_word),
        "option_order": Demo("Swap the option order, change the answer?", "live", sensitivity.option_order),
        # Lesson 02
        "token_counter": Demo("Count real tokens", "free", tokens.token_counter),
        # Lesson 03
        "context_budget": Demo("Fill the context window", "free", context.context_budget),
        "history_growth": Demo("Why long chats get expensive", "free", context.history_growth),
        # Lesson 04
        "sampling_simulator": Demo("Temperature, top-k and top-p, hands on", "free", sampling.sampling_simulator),
        # Lesson 05
        "doi_checker": Demo("Is this citation real?", "free", knowledge.doi_checker),
        "citation_check": Demo("Ask Claude for citations, then check them", "live", knowledge.citation_check),
        # Lesson 06
        "attention_toy": Demo("Where does \"it\" look?", "free", transformer.attention_toy),
        "trophy_suitcase": Demo("Attention and position, tested on Claude", "live", transformer.trophy_suitcase),
        # Lesson 07
        "truncation_sim": Demo("What survives when you cut the history?", "free", long_context.truncation_sim),
        "needle_test": Demo("Needle in a haystack", "live", long_context.needle_test),
        "output_truncation": Demo("Cut the answer short with max_tokens", "live", long_context.output_truncation),
        # Chapter 5
        "contract_checker": Demo("Byte-identical vs contract-identical", "free", lessons.contract_checker),
        "prompt_versions": Demo("Five prompts, one change each", "free", lessons.prompt_versions),
        "decomposition_checker": Demo("Catch the made-up clause", "free", lessons.decomposition_checker),
        "prompt_inspector": Demo("System prompt, context or tool?", "free", lessons.prompt_inspector),
        "prompt_cost": Demo("What each prompt version costs", "free", lessons.prompt_cost),
        "prompt_lab": Demo("Prompt Lab: measure a prompt change", "live", lab.prompt_lab),
        # Chapter 6
        "json_failures": Demo("Loud vs silent: the four JSON failures", "free", ch06.json_failures),
        "constrained_decoding": Demo("Mask the tokens, compare the approaches", "free", ch06.constrained_decoding),
        "schema_checker": Demo("Honest escape hatches and checkable evidence", "free", ch06.schema_checker),
        "tool_round_trip": Demo("Step through a tool call", "free", ch06.tool_round_trip),
        "tool_guard": Demo("Guard the refund tool", "free", ch06.tool_guard),
        "validation_layers": Demo("Shape, meaning or safety: which layer catches it?", "free", ch06.validation_layers),
        "repair_loop": Demo("Repair, limit, fall back", "free", ch06.repair_loop),
    }


def get(demo_id: str) -> Demo:
    return _registry()[demo_id]
