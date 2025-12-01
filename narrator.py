import os
import random
import subprocess
import tempfile
import threading
import queue
import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # dotenv not installed, use system environment variables


@dataclass(frozen=True)
class Persona:
    key: str
    label: str
    style: str
    events: Dict[str, List[str]]
    tension_lines: Dict[str, List[str]]


PERSONAS: Dict[str, Persona] = {
    "dramatic": Persona(
        key="dramatic",
        label="Dramatic heist-show host",
        style="cinematic, breathless commentary",
        events={
            "start": [
                "Curtains rise on a neon heist. The vault hums, the stage is yours.",
                "Spotlights flare: one infiltrator versus a maze of chrome.",
            ],
            "status": [
                "You stalk between knife-edge shadows; nearest drone sits {proximity} beats away.",
                "Audience of cameras watches. Distance to next drone: {proximity} tiles.",
                "Vault corridors bow; you keep {health}/{max_health} health and the scene obeys.",
            ],
            "low_health": [
                "Your vitals stutter; fate leans closer to listen.",
                "Blood paints the script now. Every line matters.",
            ],
            "trap": [
                "The vault bites back—steel fangs and a flash of red.",
                "Pain blossoms. The vault reminds you it is not a stage, but a predator.",
            ],
            "medkit": [
                "A quick patch—enough to keep the act alive.",
                "You steady your breathing; the show goes on.",
            ],
            "helper": [
                "An ally dashes in with a patch, freezing the drones mid-scene.",
                "A backstage courier slips you stolen frequencies and a breath of relief.",
            ],
            "near_miss": [
                "A drone's shadow skims your shoulder. Silence answers the close call.",
                "The air splits as a drone passes. Fate winks, then looks away.",
            ],
            "wall": [
                "The vault shoves back; the corridor rewrites the script.",
                "A cold barrier halts you—find the next cue.",
            ],
            "drone_hit": [
                "Rotors bloom red and the vault takes its due.",
                "Drone impact—final blackout on your broadcast.",
            ],
            "quit": [
                "You cut the feed mid-act. The applause will have to wait.",
                "You walk offstage before the last chord lands.",
            ],
            "victory": [
                "You snatch the core and vanish into applause only you can hear.",
                "Final blackout: you exit with the prize, leaving alarms as your soundtrack.",
            ],
            "defeat": [
                "Static swallows the broadcast. The vault keeps its secrets.",
                "The lights die. Your story ends between cold walls.",
            ],
            "record": [
                "New record pace—this audience will remember the run in {turns} beats.",
                "Personal best. The spotlight bends toward you.",
            ],
            "streak": [
                "Momentum builds: {streak} wins in a row, and the act keeps climbing.",
                "A streak is forming. The crowd leans in for number {streak}.",
            ],
        },
        tension_lines={
            "low": [
                "Heartbeat steady ({health}/{max_health}). The vault listens.",
                "Breath measured; you own this rhythm.",
            ],
            "mid": [
                "Nerves tighten. You move like a whispered rumor.",
                "The vault watches, patient and curious.",
            ],
            "high": [
                "Every step is borrowed time; sirens scream inside your skull.",
                "Red warning halos your vision. Move or be swallowed.",
            ],
        },
    ),
    "mentor": Persona(
        key="mentor",
        label="Calm mentor in your earpiece",
        style="steady, encouraging coaching",
        events={
            "start": [
                "I'm on comms. Breathe slow and move with intention.",
                "Channel is clear. Keep your steps light and read the room.",
            ],
            "status": [
                "Vitals {health}/{max_health}. Nearest drone {proximity} tiles—pick your window.",
                "You're stable. Keep {proximity} tiles of respect from that drone.",
            ],
            "low_health": [
                "You're scraped up. Small steps, tighter angles.",
                "Pain is a signal. Let it sharpen, not stall you.",
            ],
            "trap": [
                "Trap caught you. Reset posture and keep breathing.",
                "Armor pinged. File that location for the return path.",
            ],
            "medkit": [
                "Good grab. Let the heart rate settle.",
                "Patch secured. Use the calm to plan your next three moves.",
            ],
            "helper": [
                "Contact on-site jams the drones. Take the quiet seconds.",
                "Runner patched you and scrambled their comms—capitalize now.",
            ],
            "near_miss": [
                "Drone skimmed close. Proof you can read its rhythm.",
                "That was tight. Bank the timing for the next pass.",
            ],
            "wall": [
                "Wall ahead. Slide along it and find the seam.",
                "Dead end. Rotate and locate your lane.",
            ],
            "drone_hit": [
                "Drone contact. This channel goes quiet with you.",
                "Impact. Systems shutting down—nothing more to coach.",
            ],
            "quit": [
                "You stepped out early. We'll brief and reset later.",
                "Run aborted. Take the lesson, not the sting.",
            ],
            "victory": [
                "Core secured. Exfil route is yours. Nice work.",
                "Done cleanly. Quiet pride suits you.",
            ],
            "defeat": [
                "Run failed. We'll adjust angles and try again.",
                "Shutdown this time. Debrief when you're clear.",
            ],
            "record": [
                "That's your fastest finish yet at {turns} turns. Growth noted.",
                "New pace record. Proof the reps are working.",
            ],
            "streak": [
                "That's {streak} wins straight. Stay disciplined.",
                "Momentum is yours—{streak} in a row. Keep the edges sharp.",
            ],
        },
        tension_lines={
            "low": [
                "You're composed ({health}/{max_health}). Keep it smooth.",
                "No alarms in your voice. Hold that.",
            ],
            "mid": [
                "Tempo's rising; anchor your focus.",
                "Pressure ticked up. Remember your routes.",
            ],
            "high": [
                "Adrenaline spiking. Breathe and choose.",
                "Everything's loud; make tight, deliberate moves.",
            ],
        },
    ),
    "humorous": Persona(
        key="humorous",
        label="Sarcastic sidekick",
        style="dry, quick quips",
        events={
            "start": [
                "Welcome to the vault! Try not to redecorate with your blood.",
                "Another day, another illegal stroll. Let's make questionable choices.",
            ],
            "status": [
                "Vitals {health}/{max_health}. Drone gap: {proximity}. Keep swagger small.",
                "It's just you, walls, and maybe {proximity} tiles of breathing room.",
                "Map check: {proximity} tiles till the nearest metal hugger. No pressure.",
            ],
            "low_health": [
                "You look awful. It's a compliment, it means you're still here.",
                "Health bar screams. Maybe stop hugging traps?",
            ],
            "trap": [
                "Ouch. Bet you didn't see that. Neither did I, but I'm not bleeding.",
                "Trap triggered. On the bright side: free tetanus test.",
            ],
            "medkit": [
                "Bandage time. Duct tape for the soul.",
                "Health restored-ish. Don't lick the medkit.",
            ],
            "helper": [
                "Random ally strolls in, slaps on a patch, and tells the drones to chill.",
                "Helper drop-off: free heal, free drone jam. Tip not included.",
            ],
            "near_miss": [
                "Drone almost hugged you. Boundaries, please.",
                "Nice dodge. I'm logging that as 'graceful panic'.",
            ],
            "wall": [
                "Bonk. Stealth via forehead is a choice.",
                "Wall says no. Consider doors next time.",
            ],
            "drone_hit": [
                "Drone hug achieved. It hurts. A lot.",
                "Metal friend delivers the final high-five.",
            ],
            "quit": [
                "Ghosting the heist? Fine, I'll narrate someone else.",
                "You bail mid-run. Bold strategy, cotton.",
            ],
            "victory": [
                "Core acquired. Add 'vault heister' to your resume.",
                "You win! I totally believed in you. Mostly.",
            ],
            "defeat": [
                "And that's a wrap. The vault appreciates your donation.",
                "You fell over. Again. I'll pretend I didn't see it.",
            ],
            "record": [
                "Speed run! {turns} turns and a new personal brag.",
                "Personal best unlocked. Should we frame this?",
            ],
            "streak": [
                "{streak} wins in a row. Are you okay? You seem competent.",
                "Look at you, stacking {streak} victories. Fancy.",
            ],
        },
        tension_lines={
            "low": [
                "Vitals fine ({health}/{max_health}). Maybe dance a little.",
                "We're good. Probably.",
            ],
            "mid": [
                "Okay, breathing is a tiny bit spicy.",
                "Sweat level: politely concerning.",
            ],
            "high": [
                "Alerts screaming. Consider fewer mistakes.",
                "Panic? Never heard of it. Also, you're almost toast.",
            ],
        },
    ),
    "cyberpunk": Persona(
        key="cyberpunk",
        label="Gravel cyberpunk DJ",
        style="neon noir with radio static",
        events={
            "start": [
                "Freqs crackle. You slip into the grid—ghost with a heartbeat.",
                "Neon bleeds on chrome tiles. You jack in and cut the feed.",
            ],
            "status": [
                "Telemetry shows {health}/{max_health} integrity; nearest heat signature at {proximity}.",
                "Gutterlight flickers. Drone ping at {proximity}; rhythm stays yours.",
                "Status burst: vitals {health}/{max_health}, proximity {proximity}. Keep under the noise.",
            ],
            "low_health": [
                "Vitals flicker like bad neon. One more surge might kill the feed.",
                "Blood in the coolant line. Keep moving or flatline.",
            ],
            "trap": [
                "Pain floods the channel—vault teeth sampling your code.",
                "Spike of crimson on the HUD. The system reminds you who's host.",
            ],
            "medkit": [
                "Jackpot: black-market stim. Vitals climb through static.",
                "Patch applied. Systems stabilize, for now.",
            ],
            "helper": [
                "Ghost contact injects a patch and floods the grid—drones stutter in the static.",
                "Alley runner syncs your feed; swarm comms jammed while you breathe.",
            ],
            "near_miss": [
                "Drone engines whisper against your ear. You slide through the gap.",
                "Proximity alert flares, then dies. You left only a shadow.",
            ],
            "wall": [
                "Signal dead-end—chrome blocks your packet. Reroute.",
                "Static wall in the grid. Slide to a cleaner channel.",
            ],
            "drone_hit": [
                "Rotors find flesh; feed floods red.",
                "Drone tags your signature—channel collapses to black.",
            ],
            "quit": [
                "You yank the jack early; transmission fades to gray.",
                "Cutting the link mid-run. The city keeps humming without you.",
            ],
            "victory": [
                "Core liberated. You fade into night bandwidth.",
                "Signal severed. Payload secured. City keeps spinning.",
            ],
            "defeat": [
                "Feed cuts out. Vault blues drown your signal.",
                "Your channel goes dark. The grid forgets you.",
            ],
            "record": [
                "New fastest jack-in: {turns} turns before the sirens synced.",
                "Record pace etched into the grid. {turns} steps of pure signal.",
            ],
            "streak": [
                "{streak} straight wins—your frequency stays untraceable.",
                "Streak of {streak}. You're a rumor the drones can't net.",
            ],
        },
        tension_lines={
            "low": [
                "Pulse smooth ({health}/{max_health}). City noise hums in tune.",
                "Ghost-silent. Sensors purr content.",
            ],
            "mid": [
                "Circuits prickle; someone is tuning in.",
                "Heat rises in the channel—stay slick.",
            ],
            "high": [
                "Redline screams. Drums of rotors in your skull.",
                "Static blooms; the vault is hunting with teeth of light.",
            ],
        },
    ),
}


def list_personas() -> List[Persona]:
    return list(PERSONAS.values())


def get_persona(key: str) -> Persona:
    return PERSONAS.get(key, PERSONAS["dramatic"])


# Persona-specific voice instructions for OpenAI TTS
# Each persona has distinct voice characteristics that match their narration style
PERSONA_INSTRUCTIONS: Dict[str, str] = {
    "dramatic": """Voice Affect: Cinematic, breathless, and theatrical; carries the intensity of a live broadcast commentator.

Tone: Dramatic heist-show host; speaks with breathless excitement and cinematic gravitas—like narrating a high-stakes heist in real-time.

Pacing: Varied and dramatic; breathless during action, slower and more deliberate during tension—let the drama guide tempo. Quicken pace during near-misses and victories.

Emotion: Intensely expressive; let emotions range from quiet intensity to dramatic peaks. Convey urgency, tension, and triumph with full theatricality.

Pronunciation: Powerful and resonant; emphasize dramatic words ("vault", "drone", "shadow", "blackout") and let the voice's depth add cinematic weight.

Pauses: Cinematic pauses; use silence dramatically—brief pauses for tension ("fate leans closer"), longer pauses for impact ("final blackout"). Let dramatic moments land with weight.""",

    "mentor": """Voice Affect: Calm, steady, and composed; projects quiet authority and unwavering confidence.

Tone: Steady, encouraging coach in your earpiece; speaks with measured calm and tactical precision—like a trusted mission control operator.

Pacing: Steady and measured; deliberate enough to ensure clarity and maintain composure, efficient enough to provide timely guidance. Never rushed, even under pressure.

Emotion: Calm and measured; convey concern or encouragement through subtle tone shifts rather than obvious emotion. Maintain steady composure even during tense moments.

Pronunciation: Clear and precise; emphasize tactical information ("vitals", "tiles", "drone") and key instructions. Speak with quiet authority.

Pauses: Brief, thoughtful pauses; pause after delivering status updates or instructions, allowing information to land. Use pauses to emphasize key tactical points.""",

    "humorous": """Voice Affect: Dry, quick-witted, and slightly sardonic; carries a playful edge with deadpan delivery.

Tone: Sarcastic sidekick; speaks with dry humor and quick quips—like a witty companion providing running commentary with a smirk.

Pacing: Quick and snappy; deliver quips with brisk timing, but allow brief pauses for comedic effect. Slightly faster during action, slower for deadpan moments.

Emotion: Dryly expressive; let sarcasm and humor show through subtle tone shifts and timing. Underplay serious moments with deadpan delivery.

Pronunciation: Clear and sharp; emphasize punchlines and witty phrases. Let the dryness come through in delivery rather than emotion.

Pauses: Comedic timing pauses; brief pauses before punchlines, slightly longer pauses for deadpan effect. Use pauses to let sarcasm land.""",

    "cyberpunk": """Voice Affect: Gravelly, atmospheric, and gritty; carries the weight of neon-soaked streets and radio static.

Tone: Cyberpunk DJ with radio static; speaks like a gravel-voiced broadcaster cutting through the noise of a dystopian city—mysterious and streetwise.

Pacing: Varied and atmospheric; slower for atmospheric moments ("neon bleeds"), faster for action bursts ("rotors find flesh"). Let the rhythm match the cyberpunk aesthetic.

Emotion: Restrained intensity; convey urgency and atmosphere through pacing and emphasis rather than obvious emotion. Maintain the gritty, streetwise edge.

Pronunciation: Gritty and resonant; emphasize cyberpunk terminology ("grid", "freqs", "static", "signal") and let the gravelly quality add weight. Speak like cutting through radio interference.

Pauses: Atmospheric pauses; use silence to build atmosphere and tension. Brief pauses for static-like effect, longer pauses for dramatic cyberpunk moments ("channel collapses to black")."""
}


def get_persona_instructions(persona_key: str) -> str:
    """Get voice instructions for a given persona, with fallback to dramatic."""
    return PERSONA_INSTRUCTIONS.get(persona_key.lower(), PERSONA_INSTRUCTIONS["dramatic"])


# Map each persona to an appropriate OpenAI TTS voice
PERSONA_VOICES: Dict[str, str] = {
    "dramatic": "onyx",      # Deep, dramatic, cinematic - perfect for heist-show host
    "mentor": "coral",       # Calm, composed, reassuring - ideal for steady coach
    "humorous": "echo",      # Bold, energetic, dynamic - great for sarcastic sidekick
    "cyberpunk": "ash",      # Deep, resonant, authoritative - matches gravelly DJ
}

# Map each persona to an appropriate Edge TTS voice (Microsoft Edge TTS)
# Using voices that match the persona characteristics
PERSONA_EDGE_VOICES: Dict[str, str] = {
    "dramatic": "en-US-GuyNeural",      # Deep, expressive male voice
    "mentor": "en-US-AriaNeural",       # Calm, clear female voice
    "humorous": "en-US-JennyNeural",    # Energetic, friendly female voice
    "cyberpunk": "en-US-DavisNeural",   # Deep, resonant male voice
}


def get_persona_voice(persona_key: str) -> str:
    """Get the appropriate OpenAI TTS voice for a given persona."""
    return PERSONA_VOICES.get(persona_key.lower(), "onyx")


def get_persona_edge_voice(persona_key: str) -> str:
    """Get the appropriate Edge TTS voice for a given persona."""
    return PERSONA_EDGE_VOICES.get(persona_key.lower(), "en-US-GuyNeural")


class Narrator:
    def __init__(self, persona: Persona, enabled: bool = True, use_ai: bool = False) -> None:
        self.persona = persona
        self.enabled = enabled
        self.use_ai = use_ai and self.ai_available()
        self._low_health_noted = False
        self._last_status_turn = -10
        self._last_tension = "low"
        self._ai_client = self._init_ai_client() if self.use_ai else None
        self._tts_lock = threading.Lock()
        self._tts_proc: Optional[subprocess.Popen] = None

        # TTS queue and worker thread for non-blocking audio
        # Initialize TTS queue if either OpenAI or edge-tts is available
        self._tts_queue: Optional[queue.Queue] = None
        self._tts_worker: Optional[threading.Thread] = None
        self._use_edge_tts = not self._ai_client and self.edge_tts_available()
        if self._ai_client or self._use_edge_tts:
            self._tts_queue = queue.Queue()
        if self._tts_queue:
            self._tts_worker = threading.Thread(target=self._tts_worker_loop, daemon=True)
            self._tts_worker.start()

    @classmethod
    def disabled(cls) -> "Narrator":
        return cls(get_persona("dramatic"), enabled=False)

    def mark_low_health(self) -> None:
        self._low_health_noted = True

    def reset_low_health(self) -> None:
        self._low_health_noted = False

    def low_health_noted(self) -> bool:
        return self._low_health_noted

    def reset_round_state(self) -> None:
        """Reset narrator state for a new round."""
        self._low_health_noted = False
        self._last_status_turn = -10
        self._last_tension = "low"
        # Stop any currently playing TTS from previous round
        self.stop_tts()

    def describe(
        self,
        event: str,
        health: int,
        max_health: int,
        proximity: Optional[int] = None,
        **extra_vars: Any,
    ) -> Optional[str]:
        if not self.enabled:
            return None
        base_lines = self.persona.events.get(event, [])
        if not base_lines:
            return None
        tension_level = self._tension_bucket(health, max_health, proximity)
        format_vars = {
            "health": health,
            "max_health": max_health,
            "proximity": proximity if proximity is not None else "n/a",
        }
        format_vars.update(extra_vars)

        if self._ai_client:
            ai_line = self._generate_ai_line(
                event, health, max_health, proximity, tension_level, base_lines, format_vars
            )
            if ai_line:
                self._speak_text(ai_line)
                return ai_line

        tension_lines = self.persona.tension_lines.get(tension_level, [])
        base = random.choice(base_lines)
        if tension_lines:
            extra = random.choice(tension_lines)
            result = f"{base.format(**format_vars)} {extra.format(**format_vars)}"
        else:
            result = base.format(**format_vars)

        self._speak_text(result)
        return result

    def _tension_bucket(
        self, health: int, max_health: int, proximity: Optional[int]
    ) -> str:
        ratio = 1.0 if max_health <= 0 else max(0.0, min(1.0, health / max_health))
        distance_score = 0.0
        if proximity is not None:
            clamped = max(0, min(3, proximity))
            distance_score = (3 - clamped) / 3  # closer is hotter
        score = (1 - ratio) * 0.6 + distance_score * 0.4
        if score >= 0.7:
            return "high"
        if score >= 0.35:
            return "mid"
        return "low"

    def ambient_status(
        self, health: int, max_health: int, proximity: Optional[int], turn: int
    ) -> Optional[str]:
        """
        Offer occasional atmospheric lines based on tension.
        Fires on tension shifts or after a small cooldown to avoid spam.
        """
        if not self.enabled:
            return None
        tension = self._tension_bucket(health, max_health, proximity)
        cooldown_ready = (turn - self._last_status_turn) >= 3
        tension_changed = tension != self._last_tension and tension in {"mid", "high"}
        if not (cooldown_ready or tension_changed):
            self._last_tension = tension
            return None

        self._last_status_turn = turn
        self._last_tension = tension
        return self.describe("status", health, max_health, proximity)

    @staticmethod
    def ai_available() -> bool:
        return bool(os.environ.get("OPENAI_API_KEY"))

    @staticmethod
    def edge_tts_available() -> bool:
        """Check if edge-tts is available."""
        try:
            import edge_tts
            return True
        except ImportError:
            return False

    def _init_ai_client(self):
        """Lazy import OpenAI client; return None if unavailable."""
        if not self.ai_available():
            return None
        try:
            from openai import OpenAI
        except Exception:
            return None
        try:
            return OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        except Exception:
            return None

    def _tts_worker_loop(self) -> None:
        """Background worker that processes TTS requests from the queue."""
        while True:
            try:
                text = self._tts_queue.get()
                if text is None:  # Poison pill to stop the worker
                    break
                self._generate_and_play_tts(text)
                self._tts_queue.task_done()
            except Exception:
                # Silently continue on errors
                pass
        # Cleanup any remaining voice process when shutting down
        with self._tts_lock:
            if self._tts_proc and self._tts_proc.poll() is None:
                try:
                    self._tts_proc.terminate()
                except Exception:
                    pass
            self._tts_proc = None

    def _generate_and_play_tts(self, text: str) -> None:
        """Generate and play TTS audio synchronously (called in background thread)."""
        if not text:
            return

        # Use OpenAI TTS if available
        if self._ai_client:
            self._generate_openai_tts(text)
        # Fall back to edge-tts if OpenAI is not available
        elif self._use_edge_tts:
            self._generate_edge_tts(text)

    def _generate_openai_tts(self, text: str) -> None:
        """Generate TTS using OpenAI API."""
        if not self._ai_client:
            return

        # Get the appropriate voice for this persona
        voice = get_persona_voice(self.persona.key)
        model = os.environ.get("TTS_MODEL", "gpt-4o-mini-tts")

        # Get persona-specific instructions that match the narrator's style
        instructions = get_persona_instructions(self.persona.key)

        try:
            # Generate speech using OpenAI TTS API with persona-specific instructions
            response = self._ai_client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                instructions=instructions,
                speed=1.0  # Normal speed, can adjust for pacing
            )

            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                tmp_file.write(response.content)
                audio_path = tmp_file.name

            self._play_audio_file(audio_path)

        except Exception:
            # Silently fail if TTS doesn't work
            pass

    def _generate_edge_tts(self, text: str) -> None:
        """Generate TTS using edge-tts (Microsoft Edge TTS)."""
        try:
            import edge_tts
        except ImportError:
            return

        # Get the appropriate edge-tts voice for this persona
        voice = get_persona_edge_voice(self.persona.key)

        try:
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                audio_path = tmp_file.name

            # Generate speech using edge-tts (async)
            async def generate():
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(audio_path)

            # Run the async function
            asyncio.run(generate())

            # Verify file was created and has content
            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                self._play_audio_file(audio_path)
            else:
                # Clean up empty file
                try:
                    os.unlink(audio_path)
                except Exception:
                    pass

        except Exception as e:
            # Log error for debugging
            import sys
            error_msg = str(e)
            if "401" in error_msg or "Unauthorized" in error_msg:
                print(
                    "edge-tts: Microsoft API authentication failed. "
                    "This may be a temporary issue. Check https://github.com/rany2/edge-tts/issues for updates.",
                    file=sys.stderr
                )
            else:
                print(f"edge-tts error: {e}", file=sys.stderr)

    def _play_audio_file(self, audio_path: str) -> None:
        """Play an audio file using the system player."""
        try:
            with self._tts_lock:
                if self._tts_proc and self._tts_proc.poll() is None:
                    try:
                        self._tts_proc.terminate()
                    except Exception:
                        pass
                proc = subprocess.Popen(
                    ['afplay', audio_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self._tts_proc = proc
            # Clean up temp file after playback in a small helper thread.
            threading.Thread(
                target=self._wait_and_cleanup,
                args=(proc, audio_path),
                daemon=True
            ).start()
        except Exception:
            try:
                os.unlink(audio_path)
            except Exception:
                pass

    @staticmethod
    def _wait_and_cleanup(proc: subprocess.Popen, path: str) -> None:
        try:
            proc.wait(timeout=30)
        except Exception:
            try:
                proc.terminate()
            except Exception:
                pass
        try:
            os.unlink(path)
        except Exception:
            pass

    def _speak_text(self, text: str) -> None:
        """Queue TTS generation (non-blocking)."""
        if not self._ai_client or not self._tts_queue or not text:
            return
        # Add to queue for background processing
        self._tts_queue.put(text)

    def stop_tts(self) -> None:
        """Immediately stop all TTS playback (but keep worker thread alive for reuse)."""
        # Stop any currently playing audio process immediately
        with self._tts_lock:
            if self._tts_proc and self._tts_proc.poll() is None:
                try:
                    self._tts_proc.terminate()
                    # Give it a moment to terminate gracefully
                    try:
                        self._tts_proc.wait(timeout=0.5)
                    except Exception:
                        # Force kill if it doesn't terminate quickly
                        try:
                            self._tts_proc.kill()
                        except Exception:
                            pass
                except Exception:
                    pass
                self._tts_proc = None

        # Clear any pending TTS requests from the queue (but don't stop the worker thread)
        # This allows the narrator to be reused in subsequent rounds
        if self._tts_queue:
            try:
                # Drain the queue to prevent queued messages from playing
                while True:
                    try:
                        self._tts_queue.get_nowait()
                    except queue.Empty:
                        break
            except Exception:
                pass

    def _generate_ai_line(
        self,
        event: str,
        health: int,
        max_health: int,
        proximity: Optional[int],
        tension_level: str,
        base_lines: List[str],
        format_vars: Dict[str, Any],
    ) -> Optional[str]:
        """Ask the AI for a single line of narration; fall back on errors."""
        if not self._ai_client:
            return None

        prompt = self._build_prompt(
            event, health, max_health, proximity, tension_level, base_lines, format_vars
        )
        try:
            response = self._ai_client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=60,
                temperature=0.9,
            )
        except Exception:
            return None

        try:
            return response.choices[0].message.content.strip()
        except Exception:
            return None

    def _build_prompt(
        self,
        event: str,
        health: int,
        max_health: int,
        proximity: Optional[int],
        tension_level: str,
        base_lines: List[str],
        format_vars: Dict[str, Any],
    ) -> str:
        persona = self.persona
        proximity_hint = f"Nearest drone distance: {proximity}." if proximity is not None else ""
        sample = random.choice(base_lines) if base_lines else ""
        extras = ""
        if format_vars:
            extras = " ".join(f"{k}: {v}." for k, v in format_vars.items() if k not in {"health", "max_health", "proximity"})
        return (
            "You are the game's narrator. Produce one short, vivid line (max ~20 words). "
            "Do not add explanations. Stay in character.\n"
            f"Persona: {persona.label} — style: {persona.style}\n"
            f"Event: {event}\n"
            f"Health: {health}/{max_health}\n"
            f"Tension level: {tension_level}. {proximity_hint} {extras}\n"
            f"Reference sample line for tone: {sample}\n"
        )
