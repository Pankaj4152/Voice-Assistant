

# ── Intent Labels ──────────────────────────────────────────────────────────────
INTENT_DOCS    = "DOCS"
INTENT_BROWSER = "BROWSER"
INTENT_OS      = "OS"
INTENT_AI      = "AI"
INTENT_UNKNOWN = "UNKNOWN"

ALL_INTENTS = [INTENT_DOCS, INTENT_BROWSER, INTENT_OS, INTENT_AI]


# ── Rule-Based Regex Patterns ──────────────────────────────────────────────────
# Matched against lowercased input text.
# More patterns = better coverage = fewer Gemini calls.

INTENT_PATTERNS: dict[str, list[str]] = {

    INTENT_DOCS: [
        # Document-centric commands (avoid generic 'file' so OS/file-explorer
        # commands like "open file explorer" route to the OS intent instead).
        # Only treat "open" as DOCS when it's clearly about a single document,
        # not a folder like "open documents" or "open downloads".
        r"\b(create|new|make)\b.*(document(s)?|docx?|report|note(s)?)",
        r"\bopen\b.*\b(new|a|the)\s+(document(s)?|docx?|report|note(s)?)",
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
        r"\b(click|press|tap)\b.*(button|link|element|tab|result|option|item|icon|menu)",
        r"\bscroll\b.*(up|down|left|right)",
        r"\b(fill|type|enter)\b.*(field|form|input|email|password)",
        r"\b(go back|go forward|previous page|next page|refresh|reload)\b",
        r"\b(new tab|close tab|switch tab|switch to tab|next tab|previous tab|prev tab)\b",
        r"\b(read|read out|read aloud)\b.*(page|article|content)",
        r"\bdownload\b",
        r"\b(zoom in|zoom out)\b.*(page|browser)?",
        r"\b(bookmark|add to bookmarks)\b",
        r"\b(open|go)\b.*(youtube|google|facebook|instagram|twitter|linkedin)\b",
    ],

    INTENT_OS: [
        # File explorer / known folders
        r"\b(open|go to|navigate|show)\b.*\b(file explorer|file manager|explorer)\b",
        r"\b(open|go to|navigate|show)\b.*\b(downloads?|documents?|desktop|pictures?|photos?|music|videos?|movies?)\b",

        # General app / OS controls
        r"\b(open|launch|start|run)\b.*(app|application|program|software|notepad|vscode|calculator|terminal|explorer|chrome|firefox)",
        r"\b(switch|focus)\s+to\s+(notepad|vscode|vs code|calculator|terminal|explorer|chrome|edge|firefox|settings|task manager|word|excel|powerpoint|spotify|zoom|slack|teams|discord)\b",
        r"\b(close|quit|exit|kill)\b.*(app|window|program|tab)",
        r"\b(close|quit|exit|kill)\s+(this|that|it)\b",
        r"\b(volume|brightness|wifi|bluetooth|sound)\b",
        r"\b(what(?:'s| is)?|current|check)\b.*\b(volume|sound)\b",
        r"\b(describe|explain|read|tell me)\b.*\b(screen|display)\b",
        r"\bwhat(?:'s| is)\b.*\bon\b.*\b(screen|display)\b",
        r"\b(what(?:'s| is)?|current|check)\b.*\b(battery|charge)\b",
        r"\b(battery)\b",
        r"\b(what(?:'s| is)?|current|check)\b.*\b(wi\s*-?\s*fi|wifi|wireless)\b",
        r"\b(internet|network)\b.*\b(status|connected|working|online)\b",
        r"\b(am\s+i)\b.*\b(online|offline|connected)\b",
        r"\b(which|what)\s+app\b.*\b(open|active|current)\b",
        r"\bwhere\s+am\s+i\b",
        r"\b(what(?:'s| is)?|current|tell me)\b.*\b(time|date|day)\b",
        r"\b(environment|system)\b.*\b(summary|status|report)\b",
        r"\bstatus\s+report\b",
        r"\b(screenshot|screen capture|capture screen|print screen)\b",
        r"\b(timer|stopwatch)\b",
        r"\bplay\b.*\b(music|song|audio|track|playlist)\b",
        r"\bplay\s+(something|anything)\b",
        r"\b(dim|darken|brighten)\b.*(screen|display|monitor)?",
        r"\b(copy|paste|cut|move|delete|rename)\b.*(file|folder|directory)",
        r"\b(lock|sleep|shutdown|restart|hibernate|sign out|log off)\b",
        r"\b(increase|decrease|set|mute|unmute)\b.*(volume|brightness|sound)",
        r"\b(turn up|turn down|raise|lower)\b.*(volume|sound|brightness)",
        r"\b(minimize|maximize|restore|resize)\b.*(window|all)?",
        r"\b(task manager|file manager|control panel|system settings)\b",
        r"\b(switch window|alt tab|next window)\b",
        r"\b(show desktop|task view|virtual desktop|new desktop|close desktop)\b",
        r"\b(copy|paste|cut|select all)\b",
        r"\b(empty trash|recycle bin)\b",
        r"\b(connect|disconnect)\b.*(wifi|bluetooth|internet)\b",
    ],

    INTENT_AI: [
        r"\b(what|who|when|where|why|how)\b",
        r"\b(tell me|explain|describe|summarize|define|elaborate|clarify)\b",
        r"\b(translate|convert)\b",
        r"\b(calculate|compute|solve|evaluate|math|plus|minus|times|divided)\b",
        r"\b(remind|set reminder|set alarm|schedule|add event)\b",
        r"\b(recommend|suggest|give me ideas|what should i)\b",
        r"\b(weather|news|headlines|temperature|forecast)\b",
        r"\b(time|date|today|tomorrow|day|month|year)\b",
        r"\b(joke|quote|fact|trivia|story|fun fact)\b",
        r"\b(capital|population|currency|language|president|prime minister)\b",
        r"\b(mean|means|meaning|definition|definition of)\b",
        r"\b(difference between|compare|versus|vs)\b",
        r"\b(how (much|many|long|far|tall|old|fast))\b",
        r"\b(can you|could you|would you|please)\b.*\b(tell|explain|show|help)\b",
        r"\b(i want to know|i need to know|i was wondering)\b",
    ],
}


# ── LLM System Prompt (used by Gemini fallback) ────────────────────────────────
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