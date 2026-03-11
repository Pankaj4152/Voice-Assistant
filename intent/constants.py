

# ── Intent Labels ──────────────────────────────────────────────────────────────
INTENT_DOCS    = "DOCS"
INTENT_BROWSER = "BROWSER"
INTENT_OS      = "OS"
INTENT_AI      = "AI"
INTENT_UNKNOWN = "UNKNOWN"

ALL_INTENTS = [INTENT_DOCS, INTENT_BROWSER, INTENT_OS, INTENT_AI]


# ── Rule-Based Regex Patterns ──────────────────────────────────────────────────
# Matched against lowercased input text.
# More patterns = better coverage = fewer OpenAI calls.

INTENT_PATTERNS: dict[str, list[str]] = {

    INTENT_DOCS: [
        r"\b(create|new|open|make)\b.*(document|doc|file|report|note)",
        r"\b(write|type|dictate|insert|append)\b",
        r"\b(bold|italic|underline|heading|font|format)\b",
        r"\b(save|export)\b.*(pdf|docx|txt|document)",
        r"\b(add|insert)\b.*(table|row|column|list|bullet)",
        r"\b(undo|redo)\b",
        r"\b(delete|remove)\b.*(line|word|paragraph|sentence)",
        r"\bclose\b.*(document|doc|file)",
        r"\b(select all|copy all|paste here)\b",
       # r"\b(next page|previous page|go to page)\b",
        r"\b(spell check|word count|find and replace)\b",
    ],

    INTENT_BROWSER: [
        r"\b(open|go to|navigate|visit|browse)\b.*(chrome|firefox|browser|website|url|http)",
        r"\bsearch\b.*(for\s+|on\s+|in\s+)?(google|youtube|bing|web)?",
        r"\b(click|press|tap)\b.*(button|link|element|tab)",
        r"\bscroll\b.*(up|down|left|right)",
        r"\b(fill|type|enter)\b.*(field|form|input|email|password)",
        r"\b(go back|go forward|previous page|next page|refresh|reload)\b",
        r"\b(new tab|close tab|switch tab|next tab|previous tab)\b",
        r"\b(read|read out|read aloud)\b.*(page|article|content)",
        r"\bdownload\b",
        r"\b(zoom in|zoom out)\b.*(page|browser)?",
        r"\b(bookmark|add to bookmarks)\b",
        r"\b(open|go)\b.*(youtube|google|facebook|instagram|twitter|linkedin)\b",
    ],

    INTENT_OS: [
        r"\b(open|launch|start|run)\b.*(app|application|program|software|notepad|vscode|calculator|terminal|explorer|chrome|firefox)",
        r"\b(close|quit|exit|kill)\b.*(app|window|program|tab)",
        r"\b(volume|brightness|wifi|bluetooth|sound)\b",
        r"\b(screenshot|screen capture|capture screen|print screen)\b",
        r"\b(timer|stopwatch)\b",
        r"\bplay\b.*\b(music|song)\b",
        r"\b(copy|paste|cut|move|delete|rename)\b.*(file|folder|directory)",
        r"\b(lock|sleep|shutdown|restart|hibernate|sign out|log off)\b",
        r"\b(increase|decrease|set|mute|unmute)\b.*(volume|brightness|sound)",
        r"\b(minimize|maximize|restore|resize)\b.*(window|all)?",
        r"\b(task manager|file manager|control panel|system settings)\b",
        r"\b(switch window|alt tab|next window)\b",
        r"\b(empty trash|recycle bin)\b",
        r"\b(connect|disconnect)\b.*(wifi|bluetooth|internet)\b",
    ],

    INTENT_AI: [
        r"\b(what|who|when|where|why|how)\b",
        r"\b(tell me|explain|describe|summarize|define|elaborate)\b",
        r"\b(translate|convert)\b",
        r"\b(calculate|compute|solve|evaluate)\b",
        r"\b(remind|set reminder|set alarm|schedule|add event)\b",
        r"\b(recommend|suggest|give me ideas|what should i)\b",
        r"\b(weather|news|headlines|temperature)\b",
        r"\b(time|date|today|tomorrow|day|month|year)\b",
        r"\b(joke|quote|fact|trivia)\b",
    ],
}


# ── OpenAI System Prompt ────────────────────────────────────────────────────────
LLM_SYSTEM_PROMPT = """You are an intent classifier for a voice-controlled computer assistant.
Classify the user's voice command into EXACTLY one of these 4 intents:

DOCS     → document creation, editing, formatting, saving files
BROWSER  → web browsing, searching, clicking links, filling forms
OS       → launching apps, file operations, volume, screenshot, system controls
AI       → general questions, calculations, translations, knowledge queries

Strict rules:
- Reply with ONLY one word: DOCS, BROWSER, OS, or AI
- No explanation. No punctuation. No extra text whatsoever.

Examples:
"create a new document"        → DOCS
"open youtube"                 → BROWSER
"take a screenshot"            → OS
"what is the capital of India" → AI
"play some music"              → AI
"dim the screen"               → OS
"""