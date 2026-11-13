"""Transparent scientific query interpretation."""

import re


def interpret_query(question):
    """Apply CO2RR context only to ambiguous catalyst questions."""

    original = str(question).strip()
    q = original.casefold()

    result = {
        "original_question": original,
        "search_question": original,
        "context_applied": False,
        "domain": "user_specified_or_unspecified",
        "context_note": "",
    }

    # Never override an explicitly specified scientific process.
    co2_context = (
        "co₂" in q
        or bool(re.search(
            r"\b(co2|co2rr|carbon dioxide|"
            r"electroreduction|electrochemical reduction)\b",
            q,
        ))
    )

    other_process = bool(re.search(
        r"\b(steam cracking|bioethanol|ethane cracking|"
        r"ethanol dehydration|petrochemical|"
        r"oxidative dehydrogenation|ethylene glycol)\b",
        q,
    ))

    if co2_context or other_process:
        return result

    ethylene = bool(re.search(
        r"\b(ethylene|c2h4)\b", q
    ))

    catalyst = bool(re.search(
        r"\b(catalyst|catalysts|electrocatalyst|"
        r"electrocatalysts|catalytic)\b",
        q,
    ))

    if ethylene and catalyst:
        result.update({
            "context_applied": True,
            "domain": "co2_electroreduction",
            "search_question": (
                "Electrocatalysts for electrochemical CO2 "
                "reduction to ethylene (C2H4); "
                "Cu-based catalysts, Faradaic efficiency "
                "for ethylene, ethylene partial current "
                "density, catalyst stability, cell "
                "configuration and operating conditions"
            ),
            "context_note": (
                "Interpreted as CO2 electroreduction to "
                "ethylene because no production route "
                "was specified. Specify another process "
                "in the question to change this scope."
            ),
        })

    # PRESERVE ORIGINAL RESEARCH INTENT
    if result["context_applied"]:
        result["search_question"] = (
            "Original research question: "
            + original
            + "\nScientific search scope: "
            + result["search_question"]
        )

    return result
