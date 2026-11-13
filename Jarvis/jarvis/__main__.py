"""Run Jarvis:  python -m jarvis   (see README.md for options)."""
import argparse
import re
import sys
import time
import webbrowser
from datetime import datetime

from .config import load_config

FRESH_CONVERSATION_AFTER = 30 * 60  # forget the chat after 30 minutes asleep


def greeting(title: str, weather_line: str) -> str:
    hour = datetime.now().hour
    part = "morning" if 5 <= hour < 12 else "afternoon" if hour < 18 else "evening"
    lines = [f"Good {part}, {title}."]
    if weather_line:
        lines.append(weather_line)
    lines.append("How may I help?")
    return " ".join(lines)


def main():
    ap = argparse.ArgumentParser(prog="jarvis", description="Clap twice to wake Jarvis.")
    ap.add_argument("--text", action="store_true", help="type to Jarvis instead of speaking (no microphone)")
    ap.add_argument("--no-clap", action="store_true", help="press Enter to wake Jarvis instead of clapping")
    ap.add_argument("--mute", action="store_true", help="print replies instead of speaking them")
    ap.add_argument("--calibrate", action="store_true", help="test clap detection and show sound levels")
    ap.add_argument("--say", metavar="TEXT", help="speak TEXT in Jarvis's voice and exit")
    args = ap.parse_args()

    cfg = load_config()
    title = cfg["user"].get("title", "sir")

    if args.calibrate:
        from .clap import ClapDetector
        ClapDetector(cfg).calibrate()
        return

    from .voice import Voice, chime
    voice = Voice(cfg, muted=args.mute)
    if args.say:
        voice.say(args.say)
        return

    from .apps import Apps
    from .brain import Brain
    from .weather import Weather

    print("Starting Jarvis...")
    apps = Apps(cfg)
    print(f"  found {len(apps.installed)} installed apps")
    try:
        brain = Brain(cfg, apps.names())
    except RuntimeError as e:
        sys.exit(str(e))
    weather = Weather(cfg)

    ears = None
    if not args.text:
        from .ears import Ears
        ears = Ears(cfg)
        print("  loading speech recognition (the first run downloads it, about 150 MB)...")
        ears.load()

    use_claps = not (args.text or args.no_clap)
    detector = None
    if use_claps:
        from .clap import ClapDetector
        detector = ClapDetector(cfg)

    def sound(rising):
        if not args.mute and not args.text:
            try:
                chime(rising)
            except Exception:
                pass

    def hear(wait_seconds):
        if args.text:
            try:
                return input("You: ").strip()
            except EOFError:
                raise KeyboardInterrupt
        print("  (listening...)")
        heard = ears.listen(wait_seconds)
        if heard:
            print(f"You: {heard}")
        return heard

    def act(reply):
        for name in reply.get("open_apps") or []:
            opened = apps.open(name)
            print(f"  -> opening {opened}" if opened else f"  -> couldn't find an app called {name!r}")
        for url in reply.get("open_urls") or []:
            if re.match(r"^https?://", url):
                print(f"  -> opening {url}")
                webbrowser.open(url)

    follow_up = float(cfg["ears"].get("follow_up_seconds", 7))
    last_active = 0.0
    wake_hint = "Clap twice to wake me." if use_claps else "Press Enter to wake me."
    print(f"\nJarvis is ready. {wake_hint} Press Ctrl+C to quit.\n")

    try:
        while True:
            if use_claps:
                detector.wait()
            elif not args.text:
                input("[Enter to wake] ")
            print("\n* awake *")
            if time.monotonic() - last_active > FRESH_CONVERSATION_AFTER:
                brain.forget()

            weather_line = weather.spoken()
            sound(True)
            voice.say(greeting(title, weather_line))
            context = f"Weather: {weather_line}" if weather_line else ""

            wait = follow_up + 3  # a little longer for the first request
            while True:
                heard = hear(wait)
                if not heard:
                    if args.text:
                        continue
                    break
                if args.text and heard.lower() in {"quit", "exit"}:
                    raise KeyboardInterrupt
                reply = brain.ask(heard, context)
                act(reply)
                voice.say(reply.get("say", ""))
                last_active = time.monotonic()
                if reply.get("end_conversation"):
                    break
                sound(True)
                wait = follow_up

            sound(False)
            print(f"* asleep * {wake_hint}\n")
    except KeyboardInterrupt:
        print()
        voice.say(f"Goodbye, {title}.")


if __name__ == "__main__":
    main()
