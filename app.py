import os
import re
import time
import random
import threading
import requests
import traceback
from flask import Flask

# --- FLASK APP ---
app = Flask(__name__)
STARTUP_SUCCESS = False
ERROR_MSG = ""
TOTAL_WORDS = 0
all_words = []
DEBUG_LOGS = ["App Starting..."]

# Will be set during error detection import
ERROR_TOTAL_QUESTIONS = 0
error_all_questions = []
error_is_paused = False
error_stop_session = False
error_session_stats = {}

def add_log(msg):
    print(msg)
    DEBUG_LOGS.append(msg)
    if len(DEBUG_LOGS) > 10:
        DEBUG_LOGS.pop(0)

# --- CONFIGURATION ---
TOKEN = os.getenv("BOT_TOKEN", "").strip()
DEFAULT_CHAT_ID = os.getenv("CHAT_ID", "").strip()
DATA_DIR = "content/grand-saga"

# =========================================================
# SAFE STARTUP
# =========================================================
try:
    add_log("Importing database...")
    import database as db
    
    # Parser logic
    def parse_mission2_files(data_dir="grand-saga"):
        words = []
        seen_words = set()
        # Regex updated to better handle trailing underscores
        regex = r"\*\*(?P<word>[^*]+)\*\*\s*_?\((?P<meaning>[^)]+)\)_?"
        
        # Check both the specific directory and root
        search_path = data_dir if os.path.exists(data_dir) else "."
        all_contents = os.listdir(search_path)
        add_log(f"Searching in: {os.path.abspath(search_path)}")
        add_log(f"Dir contents (first 5): {all_contents[:5]}")
            
        files = [f for f in all_contents if f.startswith("grand_saga_group") and f.endswith(".md")]
        
        def extract_num(f):
            match = re.search(r'group(\d+)', f)
            return int(match.group(1)) if match else 999
            
        files.sort(key=extract_num)
        add_log(f"Found {len(files)} files to parse.")
        
        for filename in files:
            filepath = os.path.join(search_path, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                file_word_count = 0
                for line in content.split('\n'):
                    for match in re.finditer(regex, line):
                        w_text = match.group("word").strip()
                        # Ignore Hindi text and single characters
                        if not re.search(r'[\u0900-\u097F]', w_text) and len(w_text) > 1:
                            w_upper = w_text.upper()
                            if w_upper not in seen_words:
                                words.append({
                                    "word": w_upper,
                                    "meaning": match.group("meaning").strip(),
                                    "sentence": line.replace("**", "").replace("_", "").strip(),
                                    "source": filename
                                })
                                seen_words.add(w_upper)
                                file_word_count += 1
                # add_log(f"Loaded {file_word_count} words from {filename}")
            except Exception as fe:
                add_log(f"Error reading {filename}: {fe}")
                
        return words

    add_log("Parsing words...")
    all_words = parse_mission2_files(DATA_DIR)
    TOTAL_WORDS = len(all_words)
    is_paused = False
    stop_session = False
    
    # Load Error Detection Questions
    try:
        import error_parser
        error_all_questions = error_parser.parse_error_detection_questions()
        ERROR_TOTAL_QUESTIONS = len(error_all_questions)
        add_log(f"Loaded {ERROR_TOTAL_QUESTIONS} error detection questions.")
    except Exception as ee:
        add_log(f"Failed to load error detection: {ee}")
        error_all_questions = []
        ERROR_TOTAL_QUESTIONS = 0
    
    error_is_paused = False
    error_stop_session = False
    
    STARTUP_SUCCESS = True
    add_log(f"Startup complete. Loaded {TOTAL_WORDS} words.")

except Exception as e:
    STARTUP_SUCCESS = False
    ERROR_MSG = f"CRASH DURING STARTUP:\n{traceback.format_exc()}"
    add_log(f"Startup failed: {e}")

# =========================================================
# WEB DASHBOARD
# =========================================================
@app.route('/')
def home():
    log_str = "<br>".join(DEBUG_LOGS)
    if not STARTUP_SUCCESS:
        return f"<h1>⚠️ Bot Crashed!</h1><pre>{ERROR_MSG}</pre><h3>Logs:</h3><pre>{log_str}</pre>"
    return f"<h1>Mission 2 Bot is RUNNING on Render!</h1><p>Vocab Quiz: {TOTAL_WORDS} words | Error Detection: {ERROR_TOTAL_QUESTIONS} questions</p><p>Status: {'Vocab PAUSED' if is_paused else 'Vocab RUNNING'} | {'Error PAUSED' if error_is_paused else 'Error RUNNING'}</p><p>Token: {'Set' if TOKEN else 'MISSING'}</p><h3>Live Logs:</h3><pre>{log_str}</pre>"

# =========================================================
# BOT LOGIC
# =========================================================
def send_msg(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=10).json()
        return res
    except Exception as e:
        add_log(f"Failed to send message: {e}")
        return None

# --- GLOBAL SESSION TRACKERS ---
session_stats = {} # {user_id: {"name": name, "qs": 0, "ok": 0, "ng": 0}} for vocab
error_session_stats = {} # for error detection

def show_leaderboard(chat_id):
    """Sends a professional Emoji Card style performance report for Top 20."""
    try:
        users = db.get_leaderboard(limit=20) # Show Top 20
        if not users:
            return
        
        # Count total unique participants in this batch
        total_participants = len(session_stats)
        
        report = "━━━━━━━━━━━━━━\n"
        report += "🏆 *TOP 20 LEADERBOARD* 🏆\n"
        report += f"👥 *Participants*: {total_participants}\n"
        report += "━━━━━━━━━━━━━━\n\n"
        
        for i, user in enumerate(users):
            uid = user["_id"]
            s = session_stats.get(uid, {"qs": 0, "ok": 0, "ng": 0})
            
            # Lifetime stats
            total_qs = user.get("total", 0)
            total_ok = user.get("correct", 0)
            total_per = int((total_ok / total_qs * 100)) if total_qs > 0 else 0
            
            # Current session stats
            cur_per = int((s["ok"] / s["qs"] * 100)) if s["qs"] > 0 else 0
            
            rank = i + 1
            report += f"{rank}. 👤 *{user['name'].upper()}*\n"
            report += f"✅ *Current*: `{s['ok']}/{s['qs']}` ({cur_per}%)\n"
            report += f"📈 *Lifetime*: `{total_ok}/{total_qs}` ({total_per}%)\n"
            report += "────────────────\n"
        
        send_msg(chat_id, report)
        session_stats.clear()
        
    except Exception as e:
        add_log(f"Leaderboard error: {e}")

def generate_options(word_data):
    all_meanings = list(set([w["meaning"] for w in all_words if w["meaning"] != word_data["meaning"]]))
    distractors = random.sample(all_meanings, min(3, len(all_meanings)))
    options = distractors + [word_data["meaning"]]
    random.shuffle(options)
    return [opt[:100] for opt in options], options.index(word_data["meaning"])

def start_quiz_session(chat_id, count=10, timer=15):
    global stop_session, is_paused
    add_log(f"Starting quiz thread for {chat_id}")
    stop_session = False
    is_paused = False

    try:
        state = db.get_state()
        start_idx = state["last_sent_index"] + 1
    except Exception as e:
        add_log(f"Database error in thread: {e}")
        send_msg(chat_id, f"Database error: {e}")
        return

    if start_idx >= TOTAL_WORDS:
        send_msg(chat_id, "🎉 *Congratulations!* Aapne saare words complete kar liye hain!")
        return

    end_idx = min(start_idx + count, TOTAL_WORDS)
    send_msg(chat_id, f"🚀 *Mission 2 Quiz Started!*\n📝 Words: *#{start_idx+1}* to *#{end_idx}*\n⏱️ Timer: *{timer}s* per question")

    for i in range(start_idx, end_idx):
        if stop_session: break
        while is_paused:
            if stop_session: break
            time.sleep(1)
        if stop_session: break

        word_data = all_words[i]
        options, correct_index = generate_options(word_data)
        question = f"💎 Mission 2 #{i+1}: {word_data['word']} 💎"
        explanation = f"✅ Correct: {word_data['meaning']}\n\n📖 {word_data['sentence']}"[:197]

        poll_payload = {
            "chat_id": chat_id, "question": question, "options": options,
            "is_anonymous": False, "type": "quiz", "correct_option_id": correct_index,
            "explanation": explanation, "open_period": timer
        }

        try:
            res = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPoll", json=poll_payload, timeout=20).json()
            if res.get("ok"):
                db.add_active_poll(res["result"]["poll"]["id"], correct_index, chat_id)
                db.save_state(i)
                if i < end_idx - 1: time.sleep(timer + 2)
            else:
                add_log(f"Poll failed: {res}")
                time.sleep(5)
        except Exception as e:
            add_log(f"Poll error: {e}")
            time.sleep(5)

    send_msg(chat_id, "Quiz Batch Complete!\nTotal Completed: " + str(end_idx) + " / " + str(TOTAL_WORDS) + "\nSend /quiz to continue!")
    show_leaderboard(chat_id)

# =========================================================
# ERROR DETECTION QUIZ FUNCTIONS
# =========================================================

def show_error_leaderboard(chat_id):
    """Sends error detection session performance report."""
    try:
        if not error_session_stats:
            send_msg(chat_id, "No participants in this error detection session.")
            return
        
        sorted_users = sorted(error_session_stats.items(), key=lambda x: x[1]["ok"], reverse=True)
        total_participants = len(sorted_users)
        
        medals = ["🥇", "🥈", "🥉"]
        report = "━━━━━━━━━━━━━━━━━━━━\n"
        report += "📊 *ERROR DETECTION SCORES* 📊\n"
        report += f"👥 *Participants*: {total_participants}\n"
        report += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, (uid, s) in enumerate(sorted_users[:10]):
            cur_per = int((s["ok"] / s["qs"] * 100)) if s["qs"] > 0 else 0
            rank = i + 1
            icon = medals[i] if i < 3 else f"{rank}."
            report += f"{icon} *{s['name'].upper()}*\n"
            report += f"   ✅ `{s['ok']}/{s['qs']}` ({cur_per}%)\n"
            report += "─────────────────\n"
        
        send_msg(chat_id, report)
        error_session_stats.clear()
        
    except Exception as e:
        add_log(f"Error leaderboard error: {e}")


def start_error_quiz_session(chat_id, count=10, timer=20):
    """Starts an Error Detection quiz session."""
    global error_stop_session, error_is_paused
    add_log(f"Starting error detection quiz for {chat_id}")
    error_stop_session = False
    error_is_paused = False

    try:
        state = db.get_error_state()
        start_idx = state["last_sent_index"] + 1
    except Exception as e:
        add_log(f"Database error in error thread: {e}")
        send_msg(chat_id, f"Database error: {e}")
        return

    if start_idx >= ERROR_TOTAL_QUESTIONS:
        send_msg(chat_id, "All error detection questions completed! You mastered them all!")
        return

    end_idx = min(start_idx + count, ERROR_TOTAL_QUESTIONS)
    send_msg(chat_id, f"━━━━━━━━━━━━━━━━━━━━\n🔍 *ERROR DETECTION QUIZ* 🔍\n━━━━━━━━━━━━━━━━━━━━\n📝 Questions: `#{start_idx+1}` to `#{end_idx}`\n⏱️ Timer: *{timer}s* each\n━━━━━━━━━━━━━━━━━━━━\n💡 *Identify the part of the sentence that contains the error*")
    time.sleep(1)

    for i in range(start_idx, end_idx):
        if error_stop_session: break
        while error_is_paused:
            if error_stop_session: break
            time.sleep(1)
        if error_stop_session: break

        q_data = error_all_questions[i]
        
        # Skip questions with invalid data
        options = q_data["options"]
        correct_index = q_data["correct_index"]
        
        if correct_index < 0 or len(options) != 4:
            add_log(f"Skipping bad question #{i+1}")
            continue
        

        # Format question - SENTENCE is main focus, Q# + topic is secondary reference
        sentence = q_data["sentence"]
        
        # Build with sentence as prominent first line
        question_text = f"{sentence}"
        
        # Q number + topic as subtle reference below
        topic = q_data.get('topic', '')
        ref_line = f"#{i+1} · {topic}" if topic else f"#{i+1}"
        if len(question_text) + len(ref_line) + 3 <= 300:
            question_text += f"\n{ref_line}"
        
        # Telegram poll question limit is 300 chars
        if len(question_text) > 300:
            question_text = question_text[:297] + "..."
        
        # Truncate long options for Telegram
        display_options = []
        for opt in options:
            if len(opt) > 100:
                display_options.append(opt[:97] + "...")
            else:
                display_options.append(opt)
        
        # Build explanation from parsed data
        opt_letter = ['A','B','C','D'][correct_index]
        
        # Extract Incorrect Part and Correct Replacement from the explanation field
        incorrect_part = ""
        correct_replacement = ""
        if q_data.get("explanation"):
            for line in q_data["explanation"].split("\n"):
                if "**Incorrect Part:**" in line:
                    incorrect_part = line.split("**Incorrect Part:**")[-1].strip()
                elif "**Correct Replacement:**" in line:
                    correct_replacement = line.split("**Correct Replacement:**")[-1].strip()
        
        explanation_text = f"✅ *Correct: Option {opt_letter}*"
        if incorrect_part:
            explanation_text += f"\n❌ *Error:* {incorrect_part[:40]}"
        if correct_replacement:
            explanation_text += f"\n✔️ *Use:* {correct_replacement[:40]}"
        
        # Telegram poll explanation limit is 200 chars
        if len(explanation_text) > 200:
            explanation_text = explanation_text[:197] + "..."

        poll_payload = {
            "chat_id": chat_id,
            "question": question_text,
            "options": display_options,
            "is_anonymous": False,
            "type": "quiz",
            "correct_option_id": correct_index,
            "explanation": explanation_text,
            "explanation_parse_mode": "Markdown",
            "open_period": timer
        }

        try:
            res = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPoll", json=poll_payload, timeout=20).json()
            if res.get("ok"):
                db.add_active_poll(res["result"]["poll"]["id"], correct_index, chat_id, quiz_type="error")
                db.save_error_state(i)
                if i < end_idx - 1: time.sleep(timer + 2)
            else:
                add_log(f"Error poll failed: {res}")
                time.sleep(5)
        except Exception as e:
            add_log(f"Error poll error: {e}")
            time.sleep(5)

    send_msg(chat_id, f"━━━━━━━━━━━━━━━━━━━━\n✅ *BATCH COMPLETE!* ✅\n━━━━━━━━━━━━━━━━━━━━\n📊 Progress: `{end_idx}` / `{ERROR_TOTAL_QUESTIONS}`\n💬 Send /errorquiz to continue!")
    show_error_leaderboard(chat_id)


def listener():
    if not STARTUP_SUCCESS: return
    add_log("🤖 Listener thread running...")
    last_update_id = 0
    global stop_session, is_paused
    
    while True:
        try:
            if not TOKEN:
                time.sleep(5)
                continue
            
            data = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params={"offset": last_update_id + 1, "timeout": 30}, timeout=40).json()
            
            if data.get("ok"):
                updates = data["result"]
                for update in updates:
                    last_update_id = update["update_id"]
                    
                    # --- HANDLE POLL ANSWERS (Scoring) ---
                    if "poll_answer" in update:
                        ans = update["poll_answer"]
                        poll_data = db.get_poll_data(ans["poll_id"])
                        if poll_data:
                            user_id = str(ans["user"]["id"])
                            user_name = ans["user"].get("first_name", "Student")
                            is_correct = (ans["option_ids"][0] == poll_data["correct_index"])
                            quiz_type = poll_data.get("quiz_type", "vocab")
                            
                            if quiz_type == "error":
                                # Error Detection Scoring
                                if user_id not in error_session_stats:
                                    error_session_stats[user_id] = {"name": user_name, "qs": 0, "ok": 0, "ng": 0}
                                error_session_stats[user_id]["qs"] += 1
                                if is_correct:
                                    error_session_stats[user_id]["ok"] += 1
                                else:
                                    error_session_stats[user_id]["ng"] += 1
                            else:
                                # Vocab Quiz Scoring
                                # 1. Update Database (Lifetime)
                                db.update_analytics(user_id, user_name, is_correct)
                                
                                # 2. Update Local Session (Current Batch)
                                if user_id not in session_stats:
                                    session_stats[user_id] = {"qs": 0, "ok": 0, "ng": 0}
                                
                                session_stats[user_id]["qs"] += 1
                                if is_correct:
                                    session_stats[user_id]["ok"] += 1
                                else:
                                    session_stats[user_id]["ng"] += 1

                    # --- HANDLE COMMANDS ---
                    elif "message" in update and "text" in update["message"]:
                        original_text = update["message"]["text"].strip()
                        text = original_text.lower()
                        chat_id = update["message"]["chat"]["id"]
                        
                        if text.startswith("/quiz"):
                            parts = text.split()
                            count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
                            timer = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 15
                            threading.Thread(target=start_quiz_session, args=(chat_id, count, timer), daemon=True).start()

                        elif text.startswith("/pause"):
                            is_paused = True
                            send_msg(chat_id, "⏸️ *Quiz Paused.* Send /resume to continue.")

                        elif text.startswith("/resume"):
                            is_paused = False
                            send_msg(chat_id, "▶️ *Quiz Resumed!*")

                        elif text.startswith("/stop"):
                            stop_session = True
                            send_msg(chat_id, "Stopping vocab quiz... leaderboard Generating....")

                        elif text.startswith("/stats") or text.startswith("/leaderboard"):
                            show_leaderboard(chat_id)

                        elif text.startswith("/setindex"):
                            try:
                                new_idx = int(text.split()[1])
                                db.save_state(new_idx - 1)
                                send_msg(chat_id, f"Progress set to word #{new_idx}")
                            except:
                                send_msg(chat_id, "Usage: /setindex 97")

                        # --- ERROR DETECTION COMMANDS ---
                        elif text.startswith("/errorquiz"):
                            parts = text.split()
                            count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
                            timer = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 20
                            if ERROR_TOTAL_QUESTIONS == 0:
                                send_msg(chat_id, "Error Detection questions not loaded. Check server logs.")
                            else:
                                threading.Thread(target=start_error_quiz_session, args=(chat_id, count, timer), daemon=True).start()

                        elif text.startswith("/epause"):
                            error_is_paused = True
                            send_msg(chat_id, "Error Detection Quiz PAUSED. Send /eresume to continue.")

                        elif text.startswith("/eresume"):
                            error_is_paused = False
                            send_msg(chat_id, "Error Detection Quiz RESUMED!")

                        elif text.startswith("/estop"):
                            error_stop_session = True
                            send_msg(chat_id, "Stopping Error Detection quiz...")

                        elif text.startswith("/estats") or text.startswith("/eleaderboard"):
                            show_error_leaderboard(chat_id)

                        elif text.startswith("/esetindex"):
                            try:
                                new_idx = int(text.split()[1])
                                db.save_error_state(new_idx - 1)
                                send_msg(chat_id, f"Error Detection progress set to question #{new_idx}")
                            except:
                                send_msg(chat_id, "Usage: /esetindex 50")

                        # --- HELP COMMAND ---
                        elif text.startswith("/help"):
                            help_text = (
                                "*Available Commands:*\n\n"
                                "*Vocab Quiz:*\n"
                                "/quiz [count] [timer] - Start vocab quiz\n"
                                "/pause - Pause vocab quiz\n"
                                "/resume - Resume vocab quiz\n"
                                "/stop - Stop vocab quiz\n"
                                "/stats - Show vocab leaderboard\n"
                                "/setindex N - Set vocab progress to word N\n\n"
                                "*Error Detection Quiz:*\n"
                                "/errorquiz [count] [timer] - Start error detection quiz\n"
                                "/epause - Pause error quiz\n"
                                "/eresume - Resume error quiz\n"
                                "/estop - Stop error quiz\n"
                                "/estats - Show error detection leaderboard\n"
                                "/esetindex N - Set error progress to question N"
                            )
                            send_msg(chat_id, help_text)

        except Exception as e:
            add_log(f"Listener Error: {e}")
            time.sleep(5)
        time.sleep(1)

if __name__ == "__main__":
    if STARTUP_SUCCESS:
        threading.Thread(target=listener, daemon=True).start()
    # Render requires binding to port 10000 or the port specified in PORT env
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
