"""
Run this file to test both parsers (Vocab + Error Detection).

Usage:
    python run_parsers.py          → Run both parsers
    python run_parsers.py vocab    → Run only vocab parser
    python run_parsers.py error    → Run only error parser
"""

import sys
import os

# Fix Windows encoding for emoji/unicode support
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def run_vocab_parser():
    """Runs the Grand Saga vocabulary parser."""
    print("=" * 60)
    print(">>  VOCABULARY PARSER (Grand Saga)")
    print("=" * 60)

    DATA_DIR = os.path.join(SCRIPT_DIR, "content", "grand-saga")

    if not os.path.exists(DATA_DIR):
        print(f"[ERROR] Directory not found: {DATA_DIR}")
        print(f"   Make sure 'content/grand-saga/' exists with grand_saga_group*.md files.")
        return []

    from word_parser import parse_mission2_files
    words = parse_mission2_files(DATA_DIR)

    if words:
        print(f"\n[OK] Total words loaded: {len(words)}")
        print("\nSample words:")
        for i, w in enumerate(words[:5]):
            print(f"   {i+1}. {w['word']}  ->  {w['meaning']}")
        if len(words) > 5:
            print(f"   ... and {len(words) - 5} more.")
    else:
        print("[ERROR] No words were parsed.")

    print()
    return words


def run_error_parser():
    """Runs the SSC Error Detection parser."""
    print("=" * 60)
    print(">>  ERROR DETECTION PARSER (SSC PYQ)")
    print("=" * 60)

    FILE_PATH = os.path.join(SCRIPT_DIR, "content", "SSC Error Detection 716 PYQ.md")

    if not os.path.exists(FILE_PATH):
        print(f"[ERROR] File not found: {FILE_PATH}")
        print(f"   Make sure 'content/SSC Error Detection 716 PYQ.md' exists.")
        return []

    from error_parser import parse_error_detection_questions
    questions = parse_error_detection_questions(FILE_PATH)

    if questions:
        print(f"\n[OK] Total questions loaded: {len(questions)}")
        print("\nSample questions:")
        for i, q in enumerate(questions[:3]):
            print(f"   Q{q['id']}. [{q['topic']}]")
            print(f"       Sentence: {q['sentence'][:70]}...")
            print(f"       Options: {', '.join(q['options'][:2])} ...")
            print(f"       Correct: Option {['A','B','C','D'][q['correct_index']]}")
        if len(questions) > 3:
            print(f"   ... and {len(questions) - 3} more.")
    else:
        print("[ERROR] No questions were parsed.")

    print()
    return questions


if __name__ == "__main__":
    args = [a.lower() for a in sys.argv[1:]]

    if not args or "vocab" in args:
        words = run_vocab_parser()
    else:
        words = []

    if not args or "error" in args:
        questions = run_error_parser()
    else:
        questions = []

    # Summary
    print("=" * 60)
    print("==  SUMMARY")
    print("=" * 60)
    if not args or "vocab" in args:
        print(f"   [VOCAB] Words loaded:      {len(words)}")
    if not args or "error" in args:
        print(f"   [ERROR] Questions loaded:  {len(questions)}")
    print("=" * 60)
