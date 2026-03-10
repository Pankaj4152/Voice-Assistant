"""
intent/test_intent.py
──────────────────────
Test suite for the intent module.

Usage:
    cd E:\\Voice-Assistant
    python -m intent.test_intent
"""

import logging
import sys

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s | %(name)s | %(message)s",
)

from intent import IntentParser, APIKeyMissingError

TEST_CASES = [
    # ── DOCS ──────────────────────────────────────────────
    ("Create a new document named Budget 2025",           "DOCS"),
    ("Write: The quarterly results are very positive",    "DOCS"),
    ("Add a table with 3 rows and 4 columns",             "DOCS"),
    ("Save and export as PDF",                            "DOCS"),
    ("Make last sentence bold",                           "DOCS"),
    ("Undo that",                                         "DOCS"),

    # ── BROWSER ───────────────────────────────────────────
    ("Open YouTube and search for Python tutorials",      "BROWSER"),
    ("Click the first result",                            "BROWSER"),
    ("Scroll down three times",                           "BROWSER"),
    ("Fill email field with test@gmail.com",              "BROWSER"),
    ("Go back to the previous page",                      "BROWSER"),
    ("Open a new tab",                                    "BROWSER"),

    # ── OS ────────────────────────────────────────────────
    ("Launch VSCode",                                     "OS"),
    ("Take a screenshot",                                 "OS"),
    ("Increase volume to 70 percent",                     "OS"),
    ("Lock the screen",                                   "OS"),
    ("Close this window",                                 "OS"),
    ("Move this file to Downloads folder",                "OS"),

    # ── AI ────────────────────────────────────────────────
    ("What is the weather today",                         "AI"),
    ("Translate hello to Hindi",                          "AI"),
    ("What is the capital of France",                     "AI"),
    ("Remind me to call mom at 5pm",                      "AI"),
    ("Calculate 25 percent of 400",                       "AI"),

    # ── Ambiguous → OpenAI handles ────────────────────────
    ("Play some music",                                   None),
    ("Dim the screen a little",                           None),
]


def run():
    parser = IntentParser()
    passed = failed = llm_used = 0

    print("\n" + "═" * 78)
    print(f"  {'COMMAND':<48} {'EXPECTED':<10} {'GOT':<10} {'METHOD'}")
    print("═" * 78)

    for command, expected in TEST_CASES:
        try:
            result = parser.parse(command)
            intent = result.intent
            method = result.method.value

            if method == "llm":
                llm_used += 1

            if expected is None:
                status = "~"   # Ambiguous — just show result
            elif intent == expected:
                status = "✓"
                passed += 1
            else:
                status = "✗"
                failed += 1

            exp = expected or "?"
            print(f"  {status} {command:<48} {exp:<10} {intent:<10} ({method})")

        except APIKeyMissingError as e:
            print(f"\n{'─'*78}")
            print(str(e))
            sys.exit(1)

        except Exception as e:
            print(f"  ✗ {command:<48} ERROR: {e}")
            failed += 1

    print("═" * 78)
    total = passed + failed
    print(f"\n  Results  : {passed}/{total} passed")
    print(f"  LLM used : {llm_used} times (OpenAI called)")
    print(f"  Rule hit : {total - llm_used} times (free, instant)\n")

    if failed == 0:
        print("  ✅ All tests passed!\n")
    else:
        print(f"  ⚠️  {failed} test(s) failed — check constants.py patterns\n")


if __name__ == "__main__":
    run()