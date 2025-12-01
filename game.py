import random
import sys
import re
import shutil
import tty
import termios
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

from audio import AudioEngine
from narrator import Narrator, get_persona, list_personas
from stats import StatsManager


Coords = Tuple[int, int]


@dataclass(frozen=True)
class Difficulty:
    name: str
    size: int
    max_health: int
    start_health: int
    wall_count: int
    trap_count: int
    medkit_count: int
    drone_count: int
    blurb: str


DIFFICULTIES: Dict[str, Difficulty] = {
    "easy": Difficulty(
        name="Easy",
        size=7,
        max_health=6,
        start_health=6,
        wall_count=7,
        trap_count=5,
        medkit_count=5,
        drone_count=1,
        blurb="Compact map, extra health, single drone.",
    ),
    "normal": Difficulty(
        name="Normal",
        size=9,
        max_health=5,
        start_health=4,
        wall_count=11,
        trap_count=8,
        medkit_count=3,
        drone_count=2,
        blurb="Original balance: 2 drones, moderate hazards.",
    ),
    "hard": Difficulty(
        name="Hard",
        size=10,
        max_health=5,
        start_health=4,
        wall_count=16,
        trap_count=14,
        medkit_count=3,
        drone_count=3,
        blurb="Bigger map, more walls and traps, extra drone.",
    ),
}
DIFFICULTY_ORDER = ("easy", "normal", "hard")
STATS_PATH = Path(__file__).with_name("stats.json")


class Colors:
    """Tiny helper for optional ANSI coloring; falls back if output is not a tty."""

    def __init__(self) -> None:
        self.enabled = sys.stdout.isatty()

    def wrap(self, text: str, code: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}\033[0m"

    def cyan(self, text: str) -> str:
        return self.wrap(text, "36")

    def yellow(self, text: str) -> str:
        return self.wrap(text, "33")

    def green(self, text: str) -> str:
        return self.wrap(text, "32")

    def red(self, text: str) -> str:
        return self.wrap(text, "31")

    def clear_screen(self) -> None:
        """Clear the terminal screen."""
        if self.enabled:
            print("\033[2J\033[H", end="")
            sys.stdout.flush()

    def save_cursor(self) -> None:
        """Save cursor position."""
        if self.enabled:
            print("\033[s", end="")
            sys.stdout.flush()

    def restore_cursor(self) -> None:
        """Restore cursor position."""
        if self.enabled:
            print("\033[u", end="")
            sys.stdout.flush()

    def move_cursor_home(self) -> None:
        """Move cursor to top-left."""
        if self.enabled:
            print("\033[H", end="")
            sys.stdout.flush()


COLORS = Colors()


class Board:
    def __init__(self, difficulty: Difficulty) -> None:
        self.difficulty = difficulty
        self.size = difficulty.size
        self.start: Coords = (0, 0)
        self.exit: Coords = (difficulty.size - 1, difficulty.size - 1)
        self.max_health = difficulty.max_health
        self.health = min(difficulty.start_health, difficulty.max_health)
        self.message_buffer: List[str] = []
        self.turns_taken = 0

        self.walls: Set[Coords] = set()
        self.traps: Set[Coords] = set()
        self.medkits: Set[Coords] = set()
        self.drones: List[Coords] = []
        self.helper: Optional[Coords] = None
        self.drone_jam_turns = 0
        self.player: Coords = self.start

        self._populate()

    def _populate(self) -> None:
        attempts = 0
        while True:
            attempts += 1
            self._reset_contents()
            self._place_features()
            if self._path_exists():
                break
            if attempts > 40:
                raise RuntimeError("Unable to create a solvable board after many attempts.")

    def _reset_contents(self) -> None:
        self.walls.clear()
        self.traps.clear()
        self.medkits.clear()
        self.drones.clear()
        self.helper = None
        self.player = self.start
        self.turns_taken = 0
        self.drone_jam_turns = 0
        self.health = min(self.difficulty.start_health, self.max_health)

    def _place_features(self) -> None:
        open_cells = set((r, c) for r in range(self.size) for c in range(self.size))
        blocked = {self.start, self.exit}

        def take_random(count: int, extra_avoid: Optional[Set[Coords]] = None) -> Set[Coords]:
            picks: Set[Coords] = set()
            avoid: Set[Coords] = set(extra_avoid or set())
            for _ in range(count):
                candidates = open_cells - blocked - avoid
                if not candidates:
                    raise RuntimeError("Not enough open cells to place all features.")
                choice = random.choice(list(candidates))
                picks.add(choice)
                blocked.add(choice)
                avoid.add(choice)
            return picks

        wall_count = self.difficulty.wall_count
        trap_count = self.difficulty.trap_count
        medkit_count = self.difficulty.medkit_count
        drone_count = self.difficulty.drone_count

        self.walls = take_random(wall_count)
        self.traps = take_random(trap_count)
        medkit_avoid = set(self._neighbors(self.start)) | set(self._neighbors(self.exit))
        self.medkits = take_random(medkit_count, extra_avoid=medkit_avoid)

        self.helper = random.choice(list(open_cells - blocked))
        blocked.add(self.helper)

        for _ in range(drone_count):
            choice = random.choice(list(open_cells - blocked))
            self.drones.append(choice)
            blocked.add(choice)

    def _path_exists(self) -> bool:
        """Ensure there's a path from start to exit ignoring traps/drones."""
        queue = [self.start]
        visited = {self.start}
        while queue:
            r, c = queue.pop(0)
            if (r, c) == self.exit:
                return True
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                nxt = (nr, nc)
                if (
                    0 <= nr < self.size
                    and 0 <= nc < self.size
                    and nxt not in self.walls
                    and nxt not in visited
                ):
                    visited.add(nxt)
                    queue.append(nxt)
        return False

    def add_message(self, message: str) -> None:
        """Add a message to the message buffer (max 5 messages)."""
        if message:
            self.message_buffer.append(message)
            # Keep only last 5 messages
            if len(self.message_buffer) > 5:
                self.message_buffer = self.message_buffer[-5:]

    def draw(self) -> None:
        # Always clear screen and move to home position for consistent display
        COLORS.clear_screen()
        legend = (
            "[P] you  [E] exit  [#] wall  [^] trap (-1 hp)  [+] medkit (+1 hp)  "
            "[D] drone  [H] helper  •  Controls: WASD or Arrow Keys, Q to quit"
        )
        header_lines = [
            COLORS.cyan(legend),
            f"Difficulty: {self.difficulty.name}   "
            f"Health: {self.health}/{self.max_health}   "
            f"Turn: {self.turns_taken}",
        ]
        grid_lines = ["    " + " ".join(str(c) for c in range(self.size))]
        for r in range(self.size):
            row = []
            for c in range(self.size):
                cell = self._cell_repr((r, c))
                row.append(cell)
            grid_lines.append(f"{r:>2} | " + " ".join(row))

        footer_lines = [COLORS.cyan("=== Recent Events ===")]
        # Always show exactly 5 lines in footer for consistent positioning
        if self.message_buffer:
            recent_messages = self.message_buffer[-5:]
            # Pad to exactly 5 lines if needed
            while len(recent_messages) < 5:
                recent_messages.append("")
            footer_lines.extend(recent_messages)
        else:
            # Show 5 empty lines to maintain consistent footer height
            footer_lines.extend(["(No recent events)"] + [""] * 4)
        footer_lines.append("")  # Final blank line

        # Center only the grid block horizontally.
        term_width, _ = shutil.get_terminal_size((100, 30))
        ansi_strip = re.compile(r"\x1b\[[0-9;]*m")

        def visible_len(text: str) -> int:
            return len(ansi_strip.sub("", text))

        grid_max = max(visible_len(line) for line in grid_lines) if grid_lines else 0
        grid_pad = " " * max(0, (term_width - grid_max) // 2)

        for line in header_lines:
            print(line)
        for line in grid_lines:
            print(f"{grid_pad}{line}")
        for line in footer_lines:
            print(line)

    def _cell_repr(self, coord: Coords) -> str:
        if coord == self.player:
            return COLORS.green("P")
        if coord == self.exit:
            return COLORS.yellow("E")
        if coord in self.walls:
            return "#"
        if coord in self.medkits:
            return COLORS.green("+")
        if coord in self.traps:
            return COLORS.red("^")
        if coord in self.drones:
            return COLORS.red("D")
        if self.helper and coord == self.helper:
            return COLORS.cyan("H")
        return "."

    def handle_player_move(self, direction: str) -> Tuple[str, Optional[str]]:
        dr, dc = {
            "w": (-1, 0),
            "s": (1, 0),
            "a": (0, -1),
            "d": (0, 1),
        }.get(direction, (0, 0))

        nr = self.player[0] + dr
        nc = self.player[1] + dc
        if not (0 <= nr < self.size and 0 <= nc < self.size):
            return "You bump into the perimeter.", "wall"
        if (nr, nc) in self.walls:
            return "That way is sealed by a wall.", "wall"

        self.player = (nr, nc)
        notice_parts: List[str] = []
        move_event: Optional[str] = None
        if self.player in self.traps:
            self.health -= 1
            self.traps.remove(self.player)
            notice_parts.append("A hidden spike nicks you. (-1 hp)")
        if self.player in self.medkits:
            self.health = min(self.max_health, self.health + 1)
            self.medkits.remove(self.player)
            notice_parts.append("You patch yourself up. (+1 hp)")
        if self.helper and self.player == self.helper:
            self.helper = None
            self.drone_jam_turns = 2
            healed = False
            if self.health < self.max_health:
                self.health = min(self.max_health, self.health + 1)
                healed = True
            helper_blurb = "A friendly runner scrambles drone signals for two turns."
            if healed:
                helper_blurb = (
                    "A friendly runner patches you up and scrambles drone signals for two turns. (+1 hp)"
                )
            notice_parts.append(helper_blurb)
            move_event = "helper"
        notice = " ".join(notice_parts)
        return notice, move_event

    def move_drones(self) -> str:
        if self.drone_jam_turns > 0:
            self.drone_jam_turns -= 1
            return "Drones buzz in place under the signal jam."
        new_positions: List[Coords] = []
        notice_parts: List[str] = []
        for idx, drone in enumerate(self.drones):
            options = self._neighbors(drone)
            options = [pos for pos in options if pos not in self.walls]
            if not options:
                new_positions.append(drone)
                continue
            # Drift randomly, bias 25% toward the player.
            if random.random() < 0.25:
                options.sort(key=lambda p: self._manhattan(p, self.player))
            next_pos = random.choice(options)
            if next_pos == self.player:
                new_positions.append(next_pos)
                notice_parts.append(f"Drone {idx + 1} crashes into you!")
            else:
                new_positions.append(next_pos)
        self.drones = new_positions
        return " ".join(notice_parts)

    def _neighbors(self, coord: Coords) -> List[Coords]:
        r, c = coord
        moves = []
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.size and 0 <= nc < self.size:
                moves.append((nr, nc))
        return moves

    def _manhattan(self, a: Coords, b: Coords) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def nearest_drone_distance(self) -> Optional[int]:
        if not self.drones:
            return None
        return min(self._manhattan(self.player, drone) for drone in self.drones)


def prompt() -> str:
    """Read a single keypress without requiring Enter. Supports arrow keys."""
    if not sys.stdout.isatty():
        # Fallback to regular input if not a TTY
        raw = input("Move (w/a/s/d/arrows) or 'q' to quit: ").strip().lower()
        return raw

    # Save terminal settings
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        # Set terminal to raw mode to read single character
        tty.setraw(fd)
        ch = sys.stdin.read(1)

        # Handle arrow keys (escape sequences)
        if ch == '\x1b':  # ESC
            ch2 = sys.stdin.read(1)
            if ch2 == '[':
                ch3 = sys.stdin.read(1)
                arrow_map = {
                    'A': 'w',  # Up arrow
                    'B': 's',  # Down arrow
                    'C': 'd',  # Right arrow
                    'D': 'a',  # Left arrow
                }
                return arrow_map.get(ch3, '')

        return ch.lower()
    finally:
        # Restore terminal settings
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def choose_difficulty() -> Tuple[str, Difficulty]:
    print(COLORS.cyan("Choose difficulty:"))
    for key in DIFFICULTY_ORDER:
        diff = DIFFICULTIES[key]
        print(f"  [{key[0]}] {diff.name}: {diff.blurb}")
    default_key = "normal"
    default_diff = DIFFICULTIES[default_key]
    mapping = {
        "e": "easy",
        "easy": "easy",
        "n": "normal",
        "normal": "normal",
        "h": "hard",
        "hard": "hard",
    }
    while True:
        raw = input("Select difficulty (e/n/h, Enter for normal): ").strip().lower()
        if raw == "":
            print(f"Defaulting to {default_diff.name}.")
            return default_key, default_diff
        if raw in mapping:
            mapped_key = mapping[raw]
            return mapped_key, DIFFICULTIES[mapped_key]
        print("Invalid choice. Use e/n/h or type the name.")


def ask_yes_no(message: str) -> bool:
    while True:
        choice = input(message).strip().lower()
        if choice in {"y", "yes"}:
            return True
        if choice in {"n", "no"}:
            return False
        print("Please answer y or n.")


def choose_narrator() -> Narrator:
    personas = list_personas()
    persona_keys = {persona.key for persona in personas}
    print(COLORS.cyan("Choose narrator style:"))
    for idx, persona in enumerate(personas, start=1):
        print(f"  [{idx}] {persona.label} ({persona.key}) — {persona.style}")

    chosen_persona = personas[0]
    while True:
        raw = input("Select narrator (number/key, Enter for default): ").strip().lower()
        if raw == "":
            break
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(personas):
                chosen_persona = personas[idx - 1]
                break
        if raw in persona_keys:
            chosen_persona = get_persona(raw)
            break
        print("Invalid choice. Use the number or persona key.")

    use_ai = Narrator.ai_available()
    if use_ai:
        print(COLORS.yellow("AI narration enabled via OPENAI_API_KEY."))
    else:
        print(COLORS.yellow("AI narration unavailable (missing OPENAI_API_KEY). Using offline lines."))

    return Narrator(chosen_persona, use_ai=use_ai)


def play_round(
    diff_key: str,
    difficulty: Difficulty,
    narrator: Narrator,
    stats: StatsManager,
    audio: AudioEngine,
) -> None:
    board = Board(difficulty)
    narrator.reset_round_state()  # Reset all narrator state for new round
    start_line = narrator.describe("start", board.health, board.max_health)
    if start_line:
        board.add_message(COLORS.yellow(start_line))

    # Clear screen before starting the game
    COLORS.clear_screen()
    audio.start_ambient()

    result = "quit"
    while True:
        board.draw()
        if board.player == board.exit:
            board.add_message(COLORS.green("You jack the vault core and slip away. Victory!"))
            victory_line = narrator.describe("victory", board.health, board.max_health)
            if victory_line:
                board.add_message(COLORS.yellow(victory_line))
            audio.play_blocking("victory")  # Play victory sound and wait for it to finish
            result = "victory"
            break
        if board.health <= 0:
            board.add_message(COLORS.red("You collapse before reaching the exit. Game over."))
            defeat_line = narrator.describe("defeat", board.health, board.max_health)
            if defeat_line:
                board.add_message(COLORS.yellow(defeat_line))
            audio.play_blocking("defeat")  # Play defeat sound and wait for it to finish
            result = "defeat"
            break

        choice = prompt()
        if choice == "q":
            narrator.stop_tts()  # Stop TTS immediately before describing quit
            board.add_message("You abandon the run.")
            quit_line = narrator.describe("quit", board.health, board.max_health)
            if quit_line:
                board.add_message(COLORS.yellow(quit_line))
            result = "quit"
            break
        if choice not in {"w", "a", "s", "d"}:
            board.add_message("Invalid input. Use w/a/s/d or q.")
            continue

        prev_health = board.health
        notice, move_event = board.handle_player_move(choice)
        if move_event == "wall":
            if notice:
                board.add_message(notice)
            wall_line = narrator.describe("wall", board.health, board.max_health)
            if wall_line:
                board.add_message(COLORS.yellow(wall_line))
            audio.play("wall")
            continue

        board.turns_taken += 1
        drone_notice = board.move_drones()
        if notice:
            board.add_message(notice)
            if move_event == "helper":
                helper_line = narrator.describe("helper", board.health, board.max_health)
                if helper_line:
                    board.add_message(COLORS.yellow(helper_line))
                audio.play("helper")
        if board.health < prev_health:
            trap_line = narrator.describe("trap", board.health, board.max_health)
            if trap_line:
                board.add_message(COLORS.yellow(trap_line))
            audio.play("trap")
        elif board.health > prev_health:
            medkit_line = narrator.describe("medkit", board.health, board.max_health)
            if medkit_line:
                board.add_message(COLORS.yellow(medkit_line))
            audio.play("medkit")
        if (
            board.health > 0
            and board.health <= max(1, board.max_health // 2)
            and not narrator.low_health_noted()
        ):
            low_line = narrator.describe("low_health", board.health, board.max_health)
            if low_line:
                narrator.mark_low_health()
                board.add_message(COLORS.yellow(low_line))
        if drone_notice:
            board.add_message(drone_notice)
        if any(drone == board.player for drone in board.drones):
            board.health = 0
            board.add_message(COLORS.red("A drone slams into you!"))
            drone_line = narrator.describe("drone_hit", board.health, board.max_health)
            if drone_line:
                board.add_message(COLORS.yellow(drone_line))
            audio.play("drone_hit")
        nearest = board.nearest_drone_distance()
        if (
            nearest is not None
            and nearest <= 1
            and board.health > 0
            and board.player != board.exit
        ):
            near_line = narrator.describe(
                "near_miss", board.health, board.max_health, proximity=nearest
            )
            if near_line:
                board.add_message(COLORS.yellow(near_line))
        if board.health > 0 and board.player != board.exit:
            status_line = narrator.ambient_status(
                board.health, board.max_health, nearest, board.turns_taken
            )
            if status_line:
                board.add_message(COLORS.yellow(status_line))

    audio.stop_all()
    stats_result = stats.record_run(diff_key, board.turns_taken, result)
    stats_line = stats.summary_line(diff_key)
    print(COLORS.cyan(f"Stats [{difficulty.name}]: {stats_line}"))
    if result == "victory" and stats_result.new_best:
        best_line = narrator.describe(
            "record",
            board.health,
            board.max_health,
            turns=board.turns_taken,
        )
        if best_line:
            print(COLORS.yellow(best_line))
    if result == "victory" and stats_result.streak >= 3:
        streak_line = narrator.describe(
            "streak",
            board.health,
            board.max_health,
            streak=stats_result.streak,
        )
        if streak_line:
            print(COLORS.yellow(streak_line))


def main() -> None:
    print(COLORS.cyan("=== SIGNAL VAULT ==="))
    print(
        "Slip through the vault, avoid drones, grab medkits, and reach the exit at the far corner."
    )
    print("Controls: w/a/s/d to move, q to quit. Walls block movement.")

    stats = StatsManager(STATS_PATH, DIFFICULTY_ORDER)
    audio = AudioEngine(enabled=True)
    if not audio.player:
        print(COLORS.yellow("No system audio player found (afplay/aplay). Continuing muted."))
        audio.enabled = False

    diff_key: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    narrator: Optional[Narrator] = None

    try:
        while True:
            if difficulty is None or narrator is None:
                diff_key, difficulty = choose_difficulty()
                stats_line = stats.summary_line(diff_key)
                print(COLORS.cyan(f"Stats [{difficulty.name}]: {stats_line}"))
                narrator = choose_narrator()
            elif diff_key:
                # On repeat runs reuse settings but show stats.
                stats_line = stats.summary_line(diff_key)
                print(COLORS.cyan(f"Stats [{difficulty.name}]: {stats_line}"))

            play_round(diff_key or "normal", difficulty, narrator, stats, audio)
            if not ask_yes_no("Play again? (y/n): "):
                print("Thanks for running the vault.")
                break
    finally:
        audio.cleanup()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSession interrupted.")
