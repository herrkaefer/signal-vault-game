import math
import shutil
import struct
import subprocess
import tempfile
import threading
import time
import wave
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


class AudioEngine:
    """
    Lightweight audio helper that generates tiny WAV clips on the fly and plays
    them with the system player (afplay/aplay). All sounds are optional.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.player = self._detect_player() if enabled else None
        self.sample_rate = 44100
        self._clips: Dict[str, str] = {}
        self._procs: List[subprocess.Popen] = []
        self._ambient_thread: Optional[threading.Thread] = None
        self._ambient_stop = threading.Event()
        self._playing_sfx: Optional[subprocess.Popen] = None  # Track currently playing SFX
        self.storage_dir: Optional[Path] = None
        try:
            self.storage_dir = Path(__file__).with_name("sounds")
            self.storage_dir.mkdir(exist_ok=True)
        except Exception:
            self.storage_dir = None

    def _detect_player(self) -> Optional[str]:
        for candidate in ("afplay", "aplay", "paplay"):
            path = shutil.which(candidate)
            if path:
                return path
        return None

    def _render_segment(
        self,
        freqs: Iterable[float],
        duration: float,
        volume: float,
        fade: float = 0.02,
        start_phase: float = 0.0,
    ) -> Tuple[List[int], float]:
        """
        Render an audio segment with smooth fading.
        Returns (samples, end_phase) for continuity between segments.
        """
        frames = int(self.sample_rate * duration)
        fade_frames = max(1, int(self.sample_rate * fade))
        freqs = list(freqs)
        if not freqs:
            # Silence segment - phase doesn't matter, return as-is
            return ([0] * frames, start_phase)

        data: List[int] = []
        for i in range(frames):
            t = i / self.sample_rate
            # Generate sample with phase continuity
            sample = sum(math.sin(2 * math.pi * f * t + start_phase) for f in freqs) / len(freqs)

            # Smooth envelope using sine curve for fade (prevents clicks)
            envelope = 1.0
            if i < fade_frames:
                # Smooth fade-in using sine curve (0 to π/2)
                fade_ratio = i / fade_frames
                envelope *= math.sin(fade_ratio * math.pi / 2)
            elif frames - i < fade_frames:
                # Smooth fade-out using sine curve (π/2 to 0)
                fade_ratio = (frames - i) / fade_frames
                envelope *= math.sin(fade_ratio * math.pi / 2)

            # Apply envelope and volume, with headroom to prevent clipping
            value = sample * envelope * volume * 0.8  # 0.8 for headroom
            # Clamp to prevent clipping
            value = max(-1.0, min(1.0, value))
            data.append(int(value * 32767))

        # Calculate end phase for continuity
        end_time = frames / self.sample_rate
        end_phase = (2 * math.pi * freqs[0] * end_time + start_phase) % (2 * math.pi)

        return (data, end_phase)

    def _write_clip(self, samples: List[int], dest: Optional[Path] = None) -> str:
        if dest:
            with wave.open(str(dest), "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit PCM
                wf.setframerate(self.sample_rate)
                frames = b"".join(struct.pack("<h", s) for s in samples)
                wf.writeframes(frames)
            return str(dest)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            with wave.open(tmp, "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit PCM
                wf.setframerate(self.sample_rate)
                frames = b"".join(struct.pack("<h", s) for s in samples)
                wf.writeframes(frames)
            return tmp.name

    def _clip(self, key: str) -> Optional[str]:
        if key in self._clips:
            return self._clips[key]

        # Reuse cached file on disk if present.
        if self.storage_dir:
            cached = self.storage_dir / f"{key}.wav"
            if cached.exists():
                self._clips[key] = str(cached)
                return str(cached)

        # Build clips lazily the first time they are used.
        # Use phase continuity to prevent clicks between segments
        samples: List[int] = []
        phase = 0.0

        if key == "ambient":
            seg, phase = self._render_segment((110, 220), 0.9, 0.12, start_phase=phase)
            samples.extend(seg)
            seg, phase = self._render_segment((), 0.08, 0.0, start_phase=phase)  # tiny pause
            samples.extend(seg)
            seg, phase = self._render_segment((180, 360), 0.7, 0.1, start_phase=phase)
            samples.extend(seg)
            seg, phase = self._render_segment((140,), 0.6, 0.08, start_phase=phase)
            samples.extend(seg)
        elif key == "trap":
            seg, phase = self._render_segment((90,), 0.12, 0.28, start_phase=phase)
            samples.extend(seg)
            seg, phase = self._render_segment((60,), 0.09, 0.24, start_phase=phase)
            samples.extend(seg)
        elif key == "medkit":
            seg, phase = self._render_segment((480,), 0.1, 0.24, start_phase=phase)
            samples.extend(seg)
            seg, phase = self._render_segment((640,), 0.1, 0.22, start_phase=phase)
            samples.extend(seg)
        elif key == "helper":
            seg, phase = self._render_segment((420, 620), 0.16, 0.2, start_phase=phase)
            samples.extend(seg)
        elif key == "wall":
            seg, phase = self._render_segment((80,), 0.08, 0.2, start_phase=phase)
            samples.extend(seg)
            seg, phase = self._render_segment((60,), 0.06, 0.16, start_phase=phase)
            samples.extend(seg)
        elif key == "drone_hit":
            seg, phase = self._render_segment((220,), 0.12, 0.26, start_phase=phase)
            samples.extend(seg)
            seg, phase = self._render_segment((180,), 0.14, 0.24, start_phase=phase)
            samples.extend(seg)
        elif key == "victory":
            seg, phase = self._render_segment((320,), 0.12, 0.22, start_phase=phase)
            samples.extend(seg)
            seg, phase = self._render_segment((), 0.02, 0.0, start_phase=phase)
            samples.extend(seg)
            seg, phase = self._render_segment((520,), 0.14, 0.24, start_phase=phase)
            samples.extend(seg)
            seg, phase = self._render_segment((720,), 0.15, 0.22, start_phase=phase)
            samples.extend(seg)
        elif key == "defeat":
            seg, phase = self._render_segment((160,), 0.16, 0.24, start_phase=phase)
            samples.extend(seg)
            seg, phase = self._render_segment((120,), 0.18, 0.22, start_phase=phase)
            samples.extend(seg)
        else:
            return None

        dest_path: Optional[Path] = None
        if self.storage_dir:
            dest_path = self.storage_dir / f"{key}.wav"
        path = self._write_clip(samples, dest=dest_path)
        self._clips[key] = path
        return path

    def _play_file(self, path: str, block: bool = False, is_sfx: bool = False) -> Optional[subprocess.Popen]:
        if not self.player:
            return None
        try:
            proc = subprocess.Popen(
                [self.player, path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if block:
                proc.wait()
            else:
                if is_sfx:
                    # Track SFX separately
                    self._playing_sfx = proc
                    # Clean up when done
                    threading.Thread(
                        target=self._wait_for_sfx,
                        args=(proc,),
                        daemon=True
                    ).start()
                else:
                    self._procs.append(proc)
            return proc
        except Exception:
            return None

    def _wait_for_sfx(self, proc: subprocess.Popen) -> None:
        """Wait for SFX to finish playing, then clear the tracking."""
        try:
            proc.wait()
        except Exception:
            pass
        finally:
            if self._playing_sfx == proc:
                self._playing_sfx = None

    def play(self, key: str) -> None:
        """
        Play a sound effect. If a sound effect is already playing, skip this one.
        Ambient sounds and victory/defeat are not affected by this check.
        """
        if not self.enabled or not self.player:
            return

        # Always allow victory and defeat sounds (they're important)
        if key in ("victory", "defeat"):
            clip = self._clip(key)
            if clip:
                self._play_file(clip, block=False, is_sfx=False)
            return

        # For other SFX, check if one is already playing
        if self._playing_sfx is not None and self._playing_sfx.poll() is None:
            # SFX is still playing, skip this one
            return

        clip = self._clip(key)
        if not clip:
            return
        self._play_file(clip, block=False, is_sfx=True)

    def play_blocking(self, key: str) -> None:
        """
        Play a sound effect and wait for it to finish (blocking).
        Used for important sounds like victory/defeat that should not be interrupted.
        """
        if not self.enabled or not self.player:
            return
        clip = self._clip(key)
        if not clip:
            return
        self._play_file(clip, block=True, is_sfx=False)

    def start_ambient(self) -> None:
        if not self.enabled or not self.player or (self._ambient_thread and self._ambient_thread.is_alive()):
            return
        clip = self._clip("ambient")
        if not clip:
            return

        self._ambient_stop.clear()

        def loop() -> None:
            while not self._ambient_stop.is_set():
                proc = self._play_file(clip, block=False)
                if not proc:
                    break
                while proc.poll() is None and not self._ambient_stop.is_set():
                    time.sleep(0.1)
                if self._ambient_stop.is_set() and proc.poll() is None:
                    try:
                        proc.terminate()
                    except Exception:
                        pass

        self._ambient_thread = threading.Thread(target=loop, daemon=True)
        self._ambient_thread.start()

    def stop_ambient(self) -> None:
        if not self._ambient_thread:
            return
        self._ambient_stop.set()
        self._ambient_thread.join(timeout=1.0)
        self._ambient_thread = None

    def stop_all(self) -> None:
        self.stop_ambient()
        # Stop currently playing SFX
        if self._playing_sfx and self._playing_sfx.poll() is None:
            try:
                self._playing_sfx.terminate()
            except Exception:
                pass
            self._playing_sfx = None
        # Clean up finished procs
        alive: List[subprocess.Popen] = []
        for proc in self._procs:
            if proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    pass
            else:
                continue
            alive.append(proc)
        self._procs = [p for p in alive if p.poll() is None]

    def cleanup(self) -> None:
        self.stop_all()
        # Keep cached clips on disk for offline reuse
        self._clips.clear()
