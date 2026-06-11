# Telegram Bot Commands — Vocab & Error Detection

---

## 📚 Vocab Quiz Commands

| Command | Description |
|---------|-------------|
| `/quiz` | Start vocab quiz (default: 10 questions, 15s timer) |
| `/quiz 20` | Start with 20 questions |
| `/quiz 20 30` | Start with 20 questions, 30 sec timer |
| `/pause` | Pause the vocab quiz |
| `/resume` | Resume the paused vocab quiz |
| `/stop` | Stop the vocab quiz completely |
| `/stats` | Show vocab leaderboard |
| `/leaderboard` | Same as /stats |
| `/setindex 100` | Set progress to word #100 |

---

## 🔍 Error Detection Commands

| Command | Description |
|---------|-------------|
| `/errorquiz` | Start error detection quiz (default: 10 questions, 20s timer) |
| `/errorquiz 15` | Start with 15 questions |
| `/errorquiz 15 25` | Start with 15 questions, 25 sec timer |
| `/epause` | Pause error detection quiz |
| `/eresume` | Resume error detection quiz |
| `/estop` | Stop error detection quiz |
| `/estats` | Show error detection leaderboard |
| `/eleaderboard` | Same as /estats |
| `/esetindex 50` | Set error progress to question #50 |

---

## 📖 Help Command

| Command | Description |
|---------|-------------|
| `/help` | Show all available commands |

---

## ⚡ Quick Usage Examples

```
/quiz              → 10 vocab questions, 15s each
/quiz 25           → 25 vocab questions, 15s each
/quiz 10 30        → 10 vocab questions, 30s each

/errorquiz         → 10 error questions, 20s each
/errorquiz 20      → 20 error questions, 20s each
/errorquiz 10 40   → 10 error questions, 40s each

/pause             → pause current quiz
/resume            → continue quiz
/stop              → end quiz
/stats             → see rankings
```

---

## 📝 Notes

- Timer value is in **seconds**
- Count can be any number (e.g., 5, 10, 15, 20, 25)
- Leaderboard resets after each batch session
- Use `/setindex N` to skip directly to word N
- Use `/esetindex N` to skip directly to error question N
