# Signal Vault

A terminal-based stealth puzzle game where you navigate through a vault, avoid security drones, collect medkits, and reach the exit—all while being narrated by dynamic AI-powered commentary.

## 📹 Demo Video

<video src="demo/signal_vault_demo.mp4" controls width="100%"></video>

*Watch the game in action: Navigate the vault, avoid drones, and experience dynamic AI narration!*

## 🎮 Game Overview

**Signal Vault** is a grid-based stealth game where you play as an infiltrator trying to steal a vault core. Navigate through a procedurally generated maze filled with:
- **Walls** - Block your path
- **Traps** - Deal damage when stepped on
- **Medkits** - Restore health
- **Drones** - Move randomly and end your run on contact
- **Helpers** - Random allies that heal you and freeze drones temporarily

Your goal: Reach the exit at the far corner while managing your health and avoiding the drones.

## ✨ Features

- **Three Difficulty Levels**: Easy, Normal, and Hard with varying map sizes and hazards
- **Dynamic AI Narration**: Choose from multiple narrator personas with unique styles
- **Text-to-Speech**: Optional TTS narration using OpenAI or edge-tts
- **Sound Effects**: Procedurally generated audio feedback for game events
- **Statistics Tracking**: Track your best times, win streaks, and performance
- **Terminal-Based**: Beautiful ANSI-colored terminal interface

## 🚀 Installation

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended) or pip

### Install Dependencies

Using `uv` (recommended):
```bash
uv sync
```

Or using `pip`:
```bash
pip install edge-tts python-dotenv openai
```

### Optional: OpenAI API Key

For AI-generated narration (instead of predefined text), set your OpenAI API key:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

Or create a `.env` file:
```
OPENAI_API_KEY=your-api-key-here
```

## 🎯 How to Play

### Running the Game

```bash
# With uv
uv run python game.py

# Or with standard Python
python game.py
```

### Controls

- **W** / **↑** - Move up
- **A** / **←** - Move left
- **S** / **↓** - Move down
- **D** / **→** - Move right
- **Q** - Quit current run

### Game Elements

- **P** - Your position (green)
- **E** - Exit (cyan)
- **#** - Wall (blocks movement)
- **^** - Trap (damages you, -1 HP)
- **+** - Medkit (restores +1 HP)
- **D** - Drone (moves randomly, instant death on contact)
- **H** - Helper (heals you and freezes drones)

### Objective

Navigate from the start position to the exit (E) in the far corner while:
- Avoiding traps that reduce your health
- Collecting medkits to restore health
- Evading drones that move randomly each turn
- Managing your health (you lose if it reaches 0)

## 🎭 Narrator Personas

Choose from four unique narrator styles, each with distinct voice characteristics:

### 1. **Dramatic** (Default)
- Style: Cinematic, breathless commentary
- Voice: Deep, dramatic, theatrical
- Perfect for: High-stakes heist atmosphere

### 2. **Mentor**
- Style: Steady, encouraging coaching
- Voice: Calm, composed, reassuring
- Perfect for: Tactical guidance and support

### 3. **Humorous**
- Style: Dry, quick quips
- Voice: Energetic, witty, sarcastic
- Perfect for: Light-hearted commentary

### 4. **Cyberpunk**
- Style: Neon noir with radio static
- Voice: Gravelly, atmospheric, gritty
- Perfect for: Dystopian tech-heist vibes

## 🔊 Text-to-Speech Options

The game supports two TTS backends:

### OpenAI TTS (Recommended)
- **Requires**: `OPENAI_API_KEY` environment variable
- **Features**:
  - AI-generated narration text (not just predefined)
  - Persona-specific voice instructions for unique delivery
  - High-quality voices (onyx, coral, echo, ash)
- **Voices**: Automatically selected based on persona

### Edge TTS (Fallback)
- **Requires**: `edge-tts` package (installed by default)
- **Features**:
  - Speaks predefined narration text
  - Free, no API key needed
  - Works offline (requires internet for generation)
- **Voices**:
  - Dramatic: `en-US-GuyNeural`
  - Mentor: `en-US-AriaNeural`
  - Humorous: `en-US-JennyNeural`
  - Cyberpunk: `en-US-DavisNeural`

**Note**: If OpenAI API key is set, OpenAI TTS is used. Otherwise, edge-tts is used automatically.

## 📊 Statistics

The game tracks:
- **Best time** (lowest turn count) per difficulty
- **Win streak** (consecutive victories)
- **Best streak** (highest streak achieved)
- **Total runs** and **victories**

Stats are saved to `stats.json` and persist between sessions.

## 🎨 Difficulty Levels

### Easy
- Map size: 7×7
- Health: 6/6
- Drones: 1
- Hazards: Fewer walls and traps

### Normal
- Map size: 9×9
- Health: 4/5
- Drones: 2
- Hazards: Balanced

### Hard
- Map size: 10×10
- Health: 4/5
- Drones: 3
- Hazards: More walls and traps

## 🛠️ Technical Details

### Project Structure

```
signal-vault/
├── game.py          # Main game logic and UI
├── narrator.py      # Narration system with TTS
├── audio.py         # Sound effects engine
├── stats.py         # Statistics tracking
├── pyproject.toml   # Dependencies
└── sounds/          # Cached audio files
```

### Dependencies

- `edge-tts` - Microsoft Edge TTS for offline narration
- `python-dotenv` - Environment variable management
- `openai` - OpenAI API for AI narration and TTS

### Audio

- Sound effects are procedurally generated WAV files
- Audio files are cached in the `sounds/` directory
- Supports `afplay` (macOS), `aplay` (Linux), and `paplay` (Linux)

## 🐛 Troubleshooting

### No Sound
- Check system volume settings
- Verify audio player is available: `which afplay` (macOS) or `which aplay` (Linux)
- For TTS issues, check error messages in terminal

### Edge-TTS 401 Error
- This indicates Microsoft's API may be temporarily unavailable
- Check [edge-tts GitHub issues](https://github.com/rany2/edge-tts/issues)
- Consider using OpenAI TTS if you have an API key

### TTS Not Working
- Verify `edge-tts` is installed: `uv run python -c "import edge_tts"`
- For OpenAI TTS, verify `OPENAI_API_KEY` is set correctly
- Check terminal for error messages

## 📝 License

This project is open source. See individual dependencies for their licenses.

## 🙏 Credits

- Built with Python 3.11+
- Uses [edge-tts](https://github.com/rany2/edge-tts) for offline TTS
- Uses OpenAI API for AI narration and TTS
- Terminal colors via ANSI escape codes

---

**Enjoy your heist!** 🎯

