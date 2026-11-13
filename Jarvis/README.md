# Jarvis

A voice assistant for your computer. Clap twice and Jarvis wakes up, greets you with the weather, answers out loud in a calm British voice, and opens your apps when you ask.

Claude is its brain, through your own **Claude Code login**. You don't need an API key.

## Setup (Windows)

1. Install Claude Code and log in, if you haven't yet. In PowerShell:
   ```powershell
   irm https://claude.ai/install.ps1 | iex
   claude        # log in once, then type /exit
   ```
2. Download this `Jarvis` folder.
3. Double-click **`jarvis.bat`**, or run `python Jarvis.py` in that folder. The first run installs everything it needs (Python packages and a ~150 MB speech-recognition model).

## Using it

| You do | Jarvis does |
|---|---|
| Clap twice | Chimes, then: *"Good evening, sir. It's 12 degrees in London, with light rain…"* |
| "Open Spotify" | Opens Spotify |
| "Open YouTube and Gmail" | Opens both in your browser |
| "What's 15% of 240?" | Answers out loud |
| *(stay silent for a few seconds)* | Goes back to sleep and waits for claps |
| "Thanks, that's all" | Goes back to sleep |

Jarvis remembers the conversation for 30 minutes, so follow-up questions work.

### Options

```
jarvis.bat --calibrate     test your claps and see sound levels
jarvis.bat --no-clap       press Enter to wake instead of clapping
jarvis.bat --text          type instead of speaking (no microphone)
jarvis.bat --say "Hello"   hear the voice
```

## Settings

Edit `config.toml` to change these:

- **What Jarvis calls you** (`title = "sir"`)
- **Your city**, if the automatic location is wrong
- **The voice.** Try `en-GB-ThomasNeural` or `en-GB-SoniaNeural`, or set `engine = "system"` for the offline Windows voice.
- **Clap sensitivity.** Raise it if Jarvis misses claps; lower it if noise wakes it.
- **Extra things to open**, like websites or folders, under `[apps]`. Start-menu apps are found automatically.

## How it works

```
microphone ─▶ clap.py   two sharp sounds 0.15–0.9 s apart
          ─▶ ears.py   records until you pause, transcribes on your PC (Whisper)
          ─▶ brain.py  sends the text to Claude via `claude -p` (your Claude Code login)
          ─▶ apps.py   opens apps and websites Claude asks for
          ─▶ voice.py  speaks the reply (Microsoft neural British voice)
weather.py: Open-Meteo, free with no key
```

Your speech is transcribed on your own computer. Only the text goes to Claude. Each request uses your Claude plan's usage the same way a Claude Code message does.

It also runs on macOS and Linux (`python -m jarvis`) but is set up and tested for Windows.
