import os
import re

import os

# Use local file in the same directory as this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ERROR_DETECTION_PATH = os.path.join(SCRIPT_DIR, "content", "SSC Error Detection 716 PYQ.md")

def parse_error_detection_questions(filepath=None):
    """
    Parses the SSC Error Detection 716 PYQ.md file and extracts questions.
    
    Returns a list of dicts with keys:
        - id: int (question number)
        - topic: str (e.g., "ALTOGETHER VS ALL TOGETHER")
        - sentence: str (the full question sentence)
        - options: list[str] (4 options A, B, C, D)
        - correct_index: int (0-3, which option is correct/wrong)
        - correct_answer_text: str (full text of the correct answer)
        - explanation: str (optional - the Expert Teacher's Explanation)
    """
    if filepath is None:
        filepath = ERROR_DETECTION_PATH
    
    if not os.path.exists(filepath):
        print(f"⚠️ Error Detection file not found at: {filepath}")
        return []
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    questions = []
    
    # Split by question headers: ### Q.<number>.
    # We'll process the file line by line for more control
    lines = content.split("\n")
    
    current_question = None
    in_options = False
    options_buffer = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Detect question start: ### Q.<num>.
        q_match = re.match(r'^###\s+Q\.(\d+)\.\s*(.+)$', stripped)
        if q_match:
            # Save previous question if exists
            if current_question:
                questions.append(current_question)
            
            q_num = int(q_match.group(1))
            topic = q_match.group(2).strip()
            current_question = {
                "id": q_num,
                "topic": topic,
                "sentence": "",
                "options": [],
                "correct_index": -1,
                "correct_answer_text": "",
                "explanation": ""
            }
            in_options = False
            options_buffer = []
            continue
        
        if current_question is None:
            continue
        
        # Detect Question line
        if stripped.startswith("**Question:**"):
            # Extract sentence - could be on this line or next
            sentence_part = stripped.replace("**Question:**", "").strip()
            if sentence_part:
                # Remove quotes if present
                sentence_part = sentence_part.strip('"').strip('"')
                current_question["sentence"] = sentence_part
            else:
                # Sentence might be on the next line
                pass
            continue
        
        # If sentence is empty but we passed Question:, grab the next non-empty line
        if not current_question["sentence"] and "Question:" in stripped:
            # Try to get sentence from this line or next
            sentence_part = stripped.split("**Question:**")[-1].strip().strip('"').strip('"')
            if sentence_part:
                current_question["sentence"] = sentence_part
            continue
        
        # Detect Options section
        if stripped == "**Options:**":
            in_options = True
            options_buffer = []
            continue
        
        # Parse options (A), (B), (C), (D) or (a), (b), (c), (d)
        if in_options:
            # First check if this line has MULTIPLE options on the same line, e.g. "(A) opt1 (b) opt2 (c) opt3 (d) opt4"
            multi_opts = re.findall(r'\(([A-Da-d])\)\s*([^(]+)', stripped)
            if len(multi_opts) >= 3:
                # Multiple options on one line - collect all
                for letter, opt_text in multi_opts:
                    options_buffer.append(opt_text.strip())
                if len(options_buffer) >= 2:
                    current_question["options"] = options_buffer
                    in_options = False
            else:
                opt_match = re.match(r'^\(([A-Da-d])\)\s*(.+)$', stripped)
                if opt_match:
                    options_buffer.append(opt_match.group(2).strip())
                    if len(options_buffer) == 4:
                        current_question["options"] = options_buffer
                        in_options = False
                elif stripped == "" or stripped.startswith("---"):
                    # Empty line or separator while in options - save whatever we have
                    if options_buffer and len(options_buffer) > 0:
                        current_question["options"] = options_buffer
                        in_options = False
        
        # Detect Correct Answer
        if "**Correct Answer:" in stripped:
            # Extract which option: (A), (B), (C), (D) or (a), (b), (c), (d)
            ans_match = re.search(r'\(([A-Da-d])\)', stripped)
            if ans_match:
                letter = ans_match.group(1).upper()
                letter_to_index = {"A": 0, "B": 1, "C": 2, "D": 3}
                current_question["correct_index"] = letter_to_index.get(letter, -1)
                current_question["correct_answer_text"] = stripped
            continue
        
        # Collect explanation text (between Correct Answer and next question or ---)
        if current_question and current_question["correct_index"] >= 0:
            # We're in the explanation zone
            if current_question["explanation"]:
                current_question["explanation"] += "\n" + stripped
            else:
                current_question["explanation"] = stripped
    
    # Don't forget the last question
    if current_question:
        questions.append(current_question)
    
    print(f"[OK] Parsed {len(questions)} error detection questions from {filepath}")
    return questions


def format_question_for_poll(q_data):
    """
    Formats a question for Telegram poll.
    Returns (question_text, options_list, correct_index)
    """
    question_text = f"🔍 Spot the Error: #{q_data['id']}\n\n"
    question_text += f"*{q_data['topic']}*\n\n"
    question_text += f"\"{q_data['sentence']}\""
    
    # Truncate if too long for Telegram (300 chars for question)
    if len(question_text) > 300:
        question_text = question_text[:297] + "..."
    
    options = q_data["options"]
    correct_index = q_data["correct_index"]
    
    return question_text, options, correct_index


if __name__ == "__main__":
    questions = parse_error_detection_questions()
    if questions:
        print(f"\nSample question #{questions[0]['id']}:")
        print(f"Topic: {questions[0]['topic']}")
        print(f"Sentence: {questions[0]['sentence'][:80]}...")
        print(f"Options: {questions[0]['options']}")
        print(f"Correct: {questions[0]['correct_index']}")
        
        q_text, opts, c_idx = format_question_for_poll(questions[0])
        print(f"\nPoll format:")
        print(f"Q: {q_text}")
        for i, opt in enumerate(opts):
            marker = "[CORRECT]" if i == c_idx else "[      ]"
            print(f"  {marker} {opt}")
