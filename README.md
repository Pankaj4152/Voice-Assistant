# Voice Assistant

Offline-first wake-word voice assistant for Windows that can:

- listen continuously for a wake word,
- transcribe spoken commands,
- classify intent,
- execute OS and browser actions,
- keep short session memory for follow-up references,
- emit telemetry for performance and debugging,
- optionally stream live state to an Electron HUD.

## What It Can Do

### 1. Voice Pipeline

End-to-end pipeline:

Mic -> VAD -> Wake Word -> ASR -> Intent -> Action

- VAD: WebRTC VAD-based speech segmentation.
- Wake word: Picovoice Porcupine with tuned sensitivity.
- ASR: Whisper-based transcription with hallucination filtering.
- Intent: rule-based first, optional Gemini fallback for ambiguous text.
- Actions: OS, browser, document/file, timer/stopwatch, and AI pass-through.

### 2. Wake Word and Follow-Up Mode

- Wake word support via Porcupine (default: jarvis).
- Frame buffering to improve detection reliability across chunk boundaries.
- Cooldown handling to reduce immediate retriggers.
- Follow-up command window (post-command) to avoid needing wake word every time.

### 3. Session Memory and Reference Resolution

The assistant remembers recent context in the current session:

- last app,
- last opened file,
- last browser URL.

This enables follow-up commands like:

- open notepad -> close this
- open a file -> delete it
- open youtube -> open this again

### 4. OS Controls (VoiceOS)

Implemented OS capabilities include:

- App launch: open notepad, open chrome, open settings, open task manager, etc.
- App close: close notepad, close app, close all apps.
- App focus/switch: switch to notepad, focus to vscode.
- Window controls: minimize, maximize, restore, close current window.
- Window switching: switch window, previous window, alt tab.
- Desktop controls:
	- show desktop,
	- task view,
	- create/switch/close virtual desktops.
- Media/system controls:
	- volume up/down/set,
	- mute/unmute,
	- brightness set/increase/decrease,
	- screenshot.
- Power/session controls:
	- lock,
	- sleep,
	- restart,
	- shutdown.
- Clipboard shortcuts:
	- copy,
	- cut,
	- paste,
	- select all.
- Timers and stopwatch:
	- set timer,
	- cancel timer,
	- start/stop/reset stopwatch.
- Music helper:
	- play music on YouTube or Spotify,
	- opens best-effort URL/app target.

Note: This layer is Windows-focused.

### 5. Browser Controls

Implemented browser capabilities include:

- open URL/site,
- search query,
- back/forward,
- refresh,
- new tab,
- close tab,
- next tab,
- previous tab,
- switch to tab N (1-9),
- scroll,
- trigger save/download dialog,
- read selected text.

### 6. Document and File Actions

Implemented DOCS actions include:

- create file,
- open file,
- delete file.

Current implementation is intentionally lightweight and not a full document editor agent yet.

### 7. AI Intent Handling

- AI intent is classified and parsed.
- AI action currently returns a structured pass-through object.
- You can plug in an answer-generation backend on top (LLM, RAG, tools, etc.).

## Command Examples

### OS Examples

- open notepad
- close this
- switch to vscode
- switch window
- previous window
- show desktop
- task view
- create new desktop
- next desktop
- close desktop
- volume 50 percent
- mute
- increase brightness
- take screenshot
- set timer for 5 minutes
- start stopwatch

### Browser Examples

- open youtube
- search for python tutorials
- new tab
- switch to tab 3
- close tab
- go back
- refresh page
- scroll down

### Follow-Up Context Examples

- open notepad -> close this
- open chrome -> switch to this
- create file named notes.txt -> open this file

## Telemetry

Telemetry is integrated across pipeline and command lifecycle.

Each session writes JSONL logs to the logs directory with:

- session id,
- stage,
- message,
- metadata,
- latency metrics,
- errors.

Telemetry stages include:

- pipeline init/start/stop,
- wake-word accepted,
- ASR completion and latency,
- intent parse latency and confidence,
- action latency and success/failure,
- command total latency,
- server state updates and HUD events,
- exceptions and failures.

## Architecture

Core modules:

- voice: VAD, wake-word detector, ASR.
- intent: classifier, parser, entity extraction.
- actions: OS/browser/files/timer/AI handlers + session memory.
- telemetry: session event logger.
- voice_server.py: WebSocket backend for Electron HUD.
- electron: overlay UI client.

## Setup

### 1. Prerequisites

- Windows machine
- Python 3.10+ (project currently running on newer Python as well)
- Microphone access
- Picovoice access key

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment variables

Create a .env file in project root:

```env
PICOVOICE_ACCESS_KEY=your_picovoice_key
GEMINI_API_KEY=your_gemini_key_optional
```

Notes:

- PICOVOICE_ACCESS_KEY is required.
- GEMINI_API_KEY is optional unless you want intent-classifier LLM fallback.

## Running

### Option A: Voice pipeline with command handler

```bash
python my_main.py
```

### Option B: Voice pipeline server for Electron HUD

```bash
python voice_server.py
```

Then start Electron app:

```bash
cd electron
npm install
npm start
```

## Testing

Run current tests:

```bash
python -m unittest test.test_voice_os_intents test.test_session_memory
```

## Current Limitations

- Primary support is Windows.
- Browser automation uses hotkeys and active-window behavior, so reliability depends on focus/state.
- File/document module is basic (create/open/delete) and not a full editor command surface yet.
- AI intent handler is pass-through and needs a response backend for full conversational answers.
- Some actions are best-effort due to OS permissions/app-specific behavior.

## Roadmap Ideas

- Stronger multi-OS abstraction layer.
- Richer doc-edit command set.
- Confirmation workflow for destructive actions.
- Per-action retry/timeout policy.
- Telemetry summary dashboard and analytics.


One OS -> multiOS


