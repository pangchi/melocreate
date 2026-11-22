#!/usr/bin/env python3
"""
MeloCreate (desktop edition)

A Python/Tkinter recreation of MeloCreate, the ringtone composer that Alan Ong
wrote for Nokia Series 40 phones (J2ME MIDP 1.0) in 2002-2003.

The editor, the duration picker, the keypad controls, the note range, the
save-record format and the Nokia Smart Messaging encoder follow the original
MIDlet. Sending by SMS (the Clickatell HTTP gateway) has been left out. In its
place the tune can be exported as a Nokia .ott file, an RTTTL string or a WAV.

Standard library only. Python 3.8+ with Tk 8.6.
"""

from __future__ import annotations

import array
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import wave
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

APP_NAME = "MeloCreate"
VERSION = "2.0"

# --------------------------------------------------------------------------
# Constants taken from the original MIDlet
# --------------------------------------------------------------------------

SIZE = 128                      # notes per ringtone
NOTE_MIN, NOTE_MAX = 22, 58     # A4 (440 Hz) .. A7 (3520 Hz), sounding pitch
NOTE_DEFAULT = 37               # C6, used when there is no previous note
TITLE_MAX = 15
SMS_PAYLOAD = 133               # 8-bit bytes in one SMS after the 7-byte port UDH

# Smart Messaging tempo table (also the RTTTL tempo list). A tempo is played
# at the first table value that is >= the tempo, as in the original ToBPM().
BPM_TABLE = [25, 28, 31, 35, 40, 45, 50, 56, 63, 70, 80, 90, 100, 112, 125,
             140, 160, 180, 200, 225, 250, 285, 320, 355, 400, 450, 500, 565,
             635, 715, 800, 900]

NAMES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NAMES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
DURATION_NAMES = ["whole", "half", "quarter", "eighth", "16th", "32nd"]
DIRECTIVE_NAMES = ["plain", "dotted", "double-dotted", "triplet"]
STYLE_NAMES = ["natural", "continuous", "staccato"]
ACCIDENTAL_SEMITONES = (1, 3, 6, 8, 10)

# Diatonic staff step (0 = C .. 6 = B) for each semitone, as drawn by Editor.drawNote
STEPS_SHARP = [0, 0, 1, 1, 2, 3, 3, 4, 4, 5, 5, 6]
STEPS_FLAT = [0, 1, 1, 2, 2, 3, 4, 4, 5, 5, 6, 6]

# Original sprite sheet (GUIComposer/UI/allStaff.png, 128 x 75), unchanged.
SPRITES_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAIAAAABLCAMAAACPz3+OAAAABGdBTUEAAK/INwWK6QAAABl0RVh0U29mdHdhcmUAQWRvYmUgSW1h"
    "Z2VSZWFkeXHJZTwAAAAGUExURQAAAP///6XZn90AAAACdFJOU/8A5bcwSgAAA5JJREFUeNpiYKQXYGBgwCYMEEAMdLQfqwsAAoiB"
    "nvZjcwFAABHnAAYqOACHOQABxECCdortx+YAgABiYKSLC3A7ACCAGBjp4gJoDGAxBCCAGBjp4gIGnGYABBADI/1cgDUXAAQQ+Q5g"
    "IGgUA4YDsBgLEEDkRQGIw8BIigADrqIQIIAY8BZTuB2AppygAAOuohgggIh1AIY0sTHAQAAABBDR5QBeBxCOEhQTkG0GCCAGImsO"
    "/EmQqCjBXigABBCxDkB3AWl5AIv90FBiAAggcrMhIfvQ8gCKA5AcxcAAEEDEF8WkOQBFOQOyg5CiH0QDBBAJlREDWTFAKBMABBAD"
    "7YtBBtS2AFoIAAQQmbUhCQ5gQE/uCPtBaQAggMisYchwACO2nM3AABBAtG8TwmIAPcKhPIAAYqCr/ahZA0wBBBA9HIAXAAQQA5GR"
    "zEAoW+DiwwMAWiWjKwAIIPIdwEAcH6ngZ0DJjFAGQABR4ACM+h4rHympITkAoRgggChxAEaLBxufAVHcIBhIKgECiGwHMGKmaex8"
    "dAegBR1AAJHvALQqDs0FcD6hTAAQQBQ4ALWSR6uvkPlICQ6z4QcQQJQ4gBG1ksedJpAcgGERQABR5ABGBpztfgZsLsDW8AUIIMoc"
    "gCdE0FwAiW4stgEEEFUdwIg7TeC0DSCAqOsA7OUAXgAQQDR0AHFJHiCAaOkALKkQ0yKAAKKpA1Ba4DhsAwgg2joAveLAYhtAAA24"
    "AwACiAFHZc5AbT4uBwAEEDS1og8/YIwGUMLH2wAFCCAGzP4BJh+jo0USH5cYBAAEENSz6J1XjM48+XyUBhEmAAggBsxqBKNaoTAA"
    "GPA6ACCAGGifAhjgjWJskQAQQAwkNHDJ5zNgH7YBAYAAok/PCL1RjAQAAoiBRn7GkQYwHQAQQHQoB/A7ACCA6FAOIDkAS4QDBBAd"
    "ygF4LsBaEgEEED3KAbyjsAABRPNygAF77oMDgADCDBpqV4WM+B0AEECESwZK+QSm3AACiA4OwA8AAohWDiDaGQABRCMHED/BBBBA"
    "tHEACRNcAAFEEweQMsEGEEDUcgChXiFOABBAVHIAnrESAgAggMh1ALEjAwQBQACR6QBix0YIA4AAIs8BxI4OEQEAAogsBxA3PkYc"
    "AAggchxA7AghUQAggMhwALFjpMQBgAAizwFEjRITBwACiCwHkMQnAAACiBwHkMYnAAACiG4LmXABgAADAJ1iIGN3kPBTAAAAAElF"
    "TkSuQmCC"
)


def play_bpm_index(tempo: int) -> int:
    for i, bpm in enumerate(BPM_TABLE):
        if tempo <= bpm:
            return i
    return len(BPM_TABLE) - 1


def play_bpm(tempo: int) -> int:
    return BPM_TABLE[play_bpm_index(tempo)]


def note_freq(note: int) -> float:
    """Sounding frequency. Note 22 is A4 = 440 Hz, one step per semitone."""
    return 440.0 * 2.0 ** ((note - 22) / 12.0)


def note_seconds(tempo: int, duration: int, directive: int) -> float:
    beat = 60.0 / play_bpm(tempo)               # a beat is a quarter note
    length = 4.0 * beat / (2 ** duration)
    return length * (1.0, 1.5, 1.75, 2.0 / 3.0)[max(0, directive)]


def note_label(duration: int, directive: int, note: int, sharp: bool = True) -> str:
    """The 'N:' text from Editor.getSelectedToString, e.g. '4C#', '8.A', '16P'."""
    value = 1 << max(0, duration)
    if directive == 3:
        value = value * 3 // 2
    text = str(value)
    if directive == 2:
        text += ".."
    elif directive == 1:
        text += "."
    if note > 0:
        text += (NAMES_SHARP if sharp else NAMES_FLAT)[(note - 1) % 12]
    else:
        text += "P"
    return text


# --------------------------------------------------------------------------
# Ringtone model (GUIComposer.Data.Ringtone)
# --------------------------------------------------------------------------

class Ringtone:
    """128 slots of (duration, directive, note, style). -1 marks an empty slot.

    duration  0..5   whole .. 1/32
    directive 0..3   none, dotted, double dotted, triplet (2/3 length)
    note      0      rest
              22..58 pitch (A4..A7), semitone steps
    style     0..2   natural, continuous, staccato
    """

    def __init__(self):
        self.clear()

    def clear(self):
        self.title = "Untitled"
        self.tempo = 120
        self.index = 0
        self.dur = [-1] * SIZE
        self.dirv = [-1] * SIZE
        self.note = [-1] * SIZE
        self.style = [-1] * SIZE

    # -- access ---------------------------------------------------------
    @staticmethod
    def _at(arr, i):
        return arr[i] if 0 <= i < SIZE else -1

    def get(self, i):
        return (self._at(self.dur, i), self._at(self.dirv, i),
                self._at(self.note, i), self._at(self.style, i))

    def set(self, i, duration=-1, directive=-1, note=-1, style=-1):
        """Like the original: only fields > -1 are written."""
        if not 0 <= i < SIZE:
            return
        if duration > -1:
            self.dur[i] = duration
        if directive > -1:
            self.dirv[i] = directive
        if note > -1:
            self.note[i] = note
        if style > -1:
            self.style[i] = style

    def set_index(self, i):
        if 0 <= i < SIZE:
            self.index = i

    def last_index(self) -> int:
        for i in range(SIZE - 1, -1, -1):
            if self.dur[i] >= 0:
                return i
        return 0

    def count(self) -> int:
        return sum(1 for d in self.dur if d >= 0)

    def is_empty(self) -> bool:
        return self.count() == 0

    # -- editing ----------------------------------------------------------
    def _arrays(self):
        return (self.dur, self.dirv, self.note, self.style)

    def insert(self, i):
        """Open an empty slot at i (the last slot falls off the end)."""
        if 0 <= i < SIZE and self.dur[i] != -1:
            for arr in self._arrays():
                arr.insert(i, -1)
                arr.pop()

    def delete(self, i):
        if 0 <= i < SIZE:
            for arr in self._arrays():
                del arr[i]
                arr.append(-1)

    def trim(self):
        """Close empty gaps left by Insert, except the one under the cursor."""
        i = 0
        while i < self.last_index():
            if self.dur[i] == -1 and i != self.index:
                self.delete(i)
                if i < self.index:
                    self.index -= 1
            else:
                i += 1

    def entries(self):
        for i in range(SIZE):
            if self.dur[i] >= 0:
                yield i, self.dur[i], max(0, self.dirv[i]), max(0, self.note[i]), max(0, self.style[i])

    # -- the original RMS record string ------------------------------------
    def to_record(self) -> str:
        title = self.title.replace(";", ",") or "Untitled"
        parts = [f"{title};{self.tempo};"]
        for i in range(SIZE):
            parts.append(f"{self.dur[i]},{self.dirv[i]},{self.note[i]},{self.style[i]};")
        return "".join(parts)

    @classmethod
    def from_record(cls, record: str) -> "Ringtone":
        rt = cls()
        fields = record.strip().split(";")
        if len(fields) < 2:
            raise ValueError("not a MeloCreate record")
        rt.title = fields[0][:TITLE_MAX] or "Untitled"
        rt.tempo = max(1, int(fields[1]))
        for i, item in enumerate(fields[2:2 + SIZE]):
            if not item:
                continue
            d, dr, n, s = (int(v) for v in item.split(","))
            rt.dur[i], rt.dirv[i], rt.note[i], rt.style[i] = d, dr, n, s
        return rt

    def copy(self) -> "Ringtone":
        rt = Ringtone.from_record(self.to_record())
        rt.index = self.index
        return rt


# --------------------------------------------------------------------------
# Nokia Smart Messaging ringtone (GUIComposer.Data.NokiaRingtone)
# --------------------------------------------------------------------------

def note_scale(note: int) -> int:
    return (note - 13) // 12          # 0..3 = Smart Messaging scale-1..scale-4


def note_value(note: int) -> int:
    return 0 if note <= 0 else (note - 1) % 12 + 1      # 0 = pause, 1 = C .. 12 = B


class BitWriter:
    def __init__(self):
        self.bits = []

    def add(self, value: int, width: int):
        for k in range(width - 1, -1, -1):
            self.bits.append((value >> k) & 1)

    def align(self):
        while len(self.bits) % 8:
            self.bits.append(0)

    def to_bytes(self) -> bytes:
        self.align()
        out = bytearray()
        for i in range(0, len(self.bits), 8):
            byte = 0
            for b in self.bits[i:i + 8]:
                byte = (byte << 1) | b
            out.append(byte)
        return bytes(out)


class BitReader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def read(self, width: int) -> int:
        value = 0
        for _ in range(width):
            byte = self.data[self.pos // 8]
            value = (value << 1) | ((byte >> (7 - self.pos % 8)) & 1)
            self.pos += 1
        return value

    def align(self):
        self.pos = (self.pos + 7) // 8 * 8


def encode_ott(rt: Ringtone, with_title: bool = True) -> bytes:
    """Build the Smart Messaging ringtone bytes (the payload the original sent).

    The 2003 MIDlet sent a 'temporary' song with no title. By default this
    version writes a 'basic' song that carries the title, which phones show
    when the ringtone is saved. Pass with_title=False for the original layout.
    """
    instructions = [[(4, 3), (play_bpm_index(rt.tempo), 5)],   # tempo
                    [(5, 3), (15, 4)]]                         # volume: max
    scale = style = None
    for _i, d, dr, n, s in rt.entries():
        if n > 0 and note_scale(n) != scale:
            scale = note_scale(n)
            instructions.append([(2, 3), (scale, 2)])
        if s != style:
            style = s
            instructions.append([(3, 3), (s, 2)])
        instructions.append([(1, 3), (note_value(n), 4), (d, 3), (dr, 2)])

    patterns = [instructions[i:i + 255] for i in range(0, len(instructions), 255)][:4]

    bw = BitWriter()
    bw.add(2, 8)                 # command length: 2 commands follow
    bw.add(0b0100101, 7)         # ringing tone programming
    bw.add(0, 1)                 # filler
    bw.add(0b0011101, 7)         # sound
    title = rt.title.encode("latin-1", "replace")[:TITLE_MAX] if with_title else b""
    if title:
        bw.add(0b001, 3)         # basic song: has a title
        bw.add(len(title), 4)
        for ch in title:
            bw.add(ch, 8)
    else:
        bw.add(0b010, 3)         # temporary song: no title
    bw.add(len(patterns), 8)     # song sequence length
    for pid, pattern in enumerate(patterns):
        bw.add(0b000, 3)         # pattern header
        bw.add(pid, 2)           # pattern A, B, C, D
        bw.add(0, 4)             # loop: none
        bw.add(len(pattern), 8)  # instructions in this pattern
        for instruction in pattern:
            for value, width in instruction:
                bw.add(value, width)
    bw.align()
    bw.add(0, 8)                 # command end
    return bw.to_bytes()


def decode_ott(data: bytes) -> Ringtone:
    """Read a Smart Messaging ringtone (.ott / hex payload) back into a Ringtone."""
    br = BitReader(data)
    rt = Ringtone()
    rt.title = "Imported"
    ncmd = br.read(8)
    for _ in range(max(1, ncmd)):
        cmd = br.read(7)
        if cmd == 0b0100101:           # ringing tone programming
            br.read(1)
            continue
        if cmd == 0b0011101:           # sound
            break
        if cmd == 0b0100010:           # unicode flag
            raise ValueError("Unicode ringtone titles are not supported")
        raise ValueError(f"unexpected command {cmd:07b}")
    song_type = br.read(3)
    if song_type == 0b001:
        length = br.read(4)
        rt.title = bytes(br.read(8) for _ in range(length)).decode("latin-1") or "Imported"
    elif song_type != 0b010:
        raise ValueError("only basic and temporary songs are supported")
    npatterns = br.read(8)
    i = 0
    scale, style = 1, 0
    for _ in range(npatterns):
        if br.read(3) != 0:
            raise ValueError("bad pattern header")
        br.read(2)
        br.read(4)
        count = br.read(8)
        for _ in range(count):
            op = br.read(3)
            if op == 1:
                value, d, dr = br.read(4), br.read(3), br.read(2)
                if i < SIZE and d <= 5:
                    if value == 0 or value > 12:
                        n = 0
                    else:
                        n = 13 + scale * 12 + (value - 1)
                        while n < NOTE_MIN:
                            n += 12
                        while n > NOTE_MAX:
                            n -= 12
                    rt.dur[i], rt.dirv[i], rt.note[i], rt.style[i] = d, dr, n, style
                    i += 1
            elif op == 2:
                scale = br.read(2)
            elif op == 3:
                style = min(2, br.read(2))
            elif op == 4:
                rt.tempo = BPM_TABLE[br.read(5)]
            elif op == 5:
                br.read(4)
            else:
                raise ValueError(f"unknown instruction {op:03b}")
    return rt


def to_rtttl(rt: Ringtone) -> str:
    name = "".join(ch for ch in rt.title if ch not in ":,") or "MeloCreate"
    tokens = []
    for _i, d, dr, n, _s in rt.entries():
        token = str(1 << d)
        if n > 0:
            token += NAMES_SHARP[(n - 1) % 12].lower() + str((n - 1) // 12 + 3)
        else:
            token += "p"
        if dr in (1, 2):
            token += "."            # RTTTL has a single dot only
        tokens.append(token)
    return f"{name[:10]}:d=4,o=5,b={play_bpm(rt.tempo)}:" + ",".join(tokens)


# --------------------------------------------------------------------------
# Sound
# --------------------------------------------------------------------------

RATE = 22050


_BLOCKS = {}


def _square(freq: float, seconds: float, volume: float = 0.28):
    """Square wave, built from a cached ~0.25 s block so long tunes render fast."""
    total = int(RATE * seconds)
    if total <= 0:
        return array.array("h")
    key = (round(freq, 3), volume)
    block = _BLOCKS.get(key)
    if block is None:
        amp = int(32767 * volume)
        period = RATE / freq
        length = round(max(1, round(0.25 * freq)) * period)
        block = array.array("h", [amp if (k % period) < period / 2 else -amp for k in range(length)])
        _BLOCKS[key] = block
    out = (block * (total // len(block) + 1))[:total]
    fade = min(int(RATE * 0.002), total // 2)
    for k in range(fade):                   # 2 ms ramps avoid clicks
        out[k] = out[k] * k // fade
        out[total - 1 - k] = out[total - 1 - k] * k // fade
    return out


def render_tune(rt: Ringtone):
    """Synthesise the tune with a square wave, like a phone buzzer.

    Returns (wav_bytes, timeline) where timeline is [(start_s, end_s, index)].
    """
    pcm = array.array("h")
    timeline = []
    t = 0.0
    for i, d, dr, n, s in rt.entries():
        length = note_seconds(rt.tempo, d, dr)
        if n > 0:
            sound = length * (0.9, 1.0, 0.5)[s]
            pcm.extend(_square(note_freq(n), sound))
            pcm.extend(array.array("h", [0]) * (int(RATE * (t + length)) - len(pcm)))
        else:
            pcm.extend(array.array("h", [0]) * (int(RATE * (t + length)) - len(pcm)))
        timeline.append((t, t + length, i))
        t += length
    pcm.extend(array.array("h", [0]) * int(RATE * 0.05))
    return pcm_to_wav(pcm), timeline


def pcm_to_wav(pcm) -> bytes:
    if sys.byteorder == "big":
        pcm = array.array("h", pcm)
        pcm.byteswap()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


class AudioOut:
    """Plays WAV data without third-party packages.

    Windows uses winsound; macOS uses afplay; Linux uses the first of paplay,
    pw-play, aplay or ffplay that is installed.
    """

    def __init__(self):
        self.proc = None
        self.until = 0.0
        self.tmpdir = tempfile.mkdtemp(prefix="melocreate-")
        self.flip = 0
        self.command = None
        self.winsound = None
        if sys.platform == "win32":
            import winsound  # noqa: WPS433
            self.winsound = winsound
        elif sys.platform == "darwin" and shutil.which("afplay"):
            self.command = ["afplay"]
        else:
            for cmd in (["paplay"], ["pw-play"], ["aplay", "-q"],
                        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]):
                if shutil.which(cmd[0]):
                    self.command = cmd
                    break

    @property
    def available(self) -> bool:
        return bool(self.winsound or self.command)

    @property
    def name(self) -> str:
        if self.winsound:
            return "winsound"
        return self.command[0] if self.command else "none"

    def play(self, wav: bytes, seconds: float):
        self.stop()
        if not self.available:
            return False
        self.flip ^= 1
        path = os.path.join(self.tmpdir, f"play{self.flip}.wav")
        with open(path, "wb") as f:
            f.write(wav)
        try:
            if self.winsound:
                self.winsound.PlaySound(path, self.winsound.SND_FILENAME | self.winsound.SND_ASYNC)
            else:
                self.proc = subprocess.Popen(self.command + [path],
                                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:      # a broken audio setup must not take the editor down
            self.proc = None
            return False
        self.until = time.monotonic() + seconds
        return True

    def stop(self):
        if self.winsound:
            try:
                self.winsound.PlaySound(None, 0)
            except Exception:
                pass
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
        self.proc = None
        self.until = 0.0

    def close(self):
        self.stop()
        shutil.rmtree(self.tmpdir, ignore_errors=True)


# --------------------------------------------------------------------------
# Saved slots (the phone's RMS record store "Ringtone")
# --------------------------------------------------------------------------

def slots_path() -> str:
    return os.path.join(os.path.expanduser("~"), ".melocreate", "slots.json")


def load_slots():
    try:
        with open(slots_path(), encoding="utf-8") as f:
            data = json.load(f)
        return [str(r) for r in data.get("records", [])]
    except (OSError, ValueError):
        return []


def save_slots(records):
    path = slots_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"format": "MeloCreate RMS records", "records": records}, f, indent=1)


# --------------------------------------------------------------------------
# Help text (the original HelpDoc screens, plus the desktop keys)
# --------------------------------------------------------------------------

HELP_EDITOR = """To enter staff
/change duration:
 FIRE(5)

Change note:
 UP(2)/DOWN(8)

Navigate:
 LEFT(4)/RIGHT(6)

Insert:
 press & hold
 ZERO(0)

Sharp/Flat:
 press & hold
 POUND(#)

Treble/Base clef:
 press & hold
 STAR(*)

First/Last note:
 press & hold
 ONE(1)/SEVEN(7)

On the computer:
 Arrows = 2/4/6/8
 Enter = 5 (FIRE)
 Hold a key for
 the press & hold
 actions.
 F1 = left soft key
 F2 = right soft key
 Esc = back
 Space = play/stop
 Ins/Del/Backspace
 = Insert/Delete/
 Clear"""

HELP_DURATION = """Select & back to Editor:
 FIRE(5)/Select

Navigate:
 LEFT(4)/RIGHT(6)
/UP(2)/DOWN(8)

Dotted/Triplet:
 POUND(#)

Cont/Stac:
 STAR(*)

Top row: rests
Bottom row: notes"""


# --------------------------------------------------------------------------
# The application
# --------------------------------------------------------------------------

HOLD_MS = 500
REPEAT_MS = 110
NAV_KEYS = {"UP", "DOWN", "LEFT", "RIGHT"}
GAME_ACTION = {"2": "UP", "8": "DOWN", "4": "LEFT", "6": "RIGHT", "5": "FIRE",
               "UP": "UP", "DOWN": "DOWN", "LEFT": "LEFT", "RIGHT": "RIGHT", "FIRE": "FIRE"}

LCD_BG = "#ffffff"
LCD_GUIDE = "#e2e2e2"
RED = "#ff0000"
PLAYHEAD = "#2a6fdb"
BODY = "#262a31"
BODY_KEY = "#3a404a"
BODY_KEY_ACTIVE = "#59616e"
BODY_TEXT = "#e8eaed"

LW, LH = 240, 128       # logical screen; the original phone was 128 x 128
SOFT_H = 14             # soft-key label strip under the screen
FONT_H = 11             # Style.FONT_HEIGHT stand-in
ROW_H = 15              # list row height


class MeloCreate(tk.Tk):
    def __init__(self, scale: int = 3, path: str | None = None):
        super().__init__()
        self.S = scale
        self.rt = Ringtone()
        self.records = load_slots()
        self.audio = AudioOut()
        self.path = None
        self.dirty = False

        # editor state (GUIComposer.UI.Editor)
        self.treble = True
        self.sharp = True
        self.start = 0
        self.preview_until = 0.0
        self.preview_on = tk.BooleanVar(value=True)

        # duration picker state (GUIComposer.UI.DurationEdit)
        self.px, self.py = 0, 0
        self.p_directive = 0
        self.p_style = 0

        # playback
        self.playing = False
        self.play_t0 = 0.0
        self.timeline = []
        self.play_index = -1
        self.play_job = None

        # screens: editor, duration, list, help
        self.screen = "editor"
        self.list_state = None
        self.help_state = None
        self.alert = None
        self.alert_job = None

        # key hold handling
        self._down = {}
        self._pending_release = {}

        self.title(APP_NAME)
        self.configure(bg=BODY)
        self.resizable(False, False)
        self._load_sprites()
        self._build_ui()
        self._build_menu()
        self._bind_keys()
        self.protocol("WM_DELETE_WINDOW", self.quit_app)
        if path:
            self.open_path(path)
        self.refresh()
        self.after(250, self._tick)

    # ------------------------------------------------------------------
    # Sprites
    # ------------------------------------------------------------------
    def _load_sprites(self):
        self.sheet = tk.PhotoImage(data=SPRITES_PNG)
        s = self.S

        def crop(x, y, w, h):
            img = tk.PhotoImage()
            img.tk.call(img, "copy", self.sheet, "-from", x, y, x + w, y + h, "-zoom", s, s)
            return img

        self.img_notes = [[crop(16 * d, 25 * o, 16, 25) for o in range(3)] for d in range(6)]
        self.img_clef = [crop(96, 0, 16, 45), crop(112, 0, 16, 45)]        # treble, bass
        self.img_acc = [crop(96, 45, 8, 13), crop(104, 45, 8, 13)]         # sharp, flat

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_ui(self):
        s = self.S
        outer = tk.Frame(self, bg=BODY, padx=18, pady=14)
        outer.pack()
        tk.Label(outer, text="MELOCREATE", bg=BODY, fg="#8a93a3",
                 font=("Helvetica", 9, "bold")).pack(pady=(0, 6))
        bezel = tk.Frame(outer, bg="#0d0f12", padx=6, pady=6)
        bezel.pack()
        self.canvas = tk.Canvas(bezel, width=LW * s, height=(LH + SOFT_H) * s,
                                bg=LCD_BG, highlightthickness=0, cursor="hand2")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", lambda e: self._wheel(+1))
        self.canvas.bind("<Button-5>", lambda e: self._wheel(-1))

        self.font_small = ("Helvetica", -int(10 * s))
        self.font_list = ("Helvetica", -int(10 * s))
        self.font_list_b = ("Helvetica", -int(10 * s), "bold")
        self.font_help = ("Helvetica", -int(10 * s))
        self.font_soft = ("Helvetica", -int(10 * s), "bold")

        pad = tk.Frame(outer, bg=BODY)
        pad.pack(pady=(12, 0))
        keys = [
            [("Options", "SOFT1"), ("▲", "UP"), ("Back", "SOFT2")],
            [("◀", "LEFT"), ("OK", "FIRE"), ("▶", "RIGHT")],
            [("", None), ("▼", "DOWN"), ("", None)],
            [("1", "1"), ("2", "2"), ("3", "3")],
            [("4", "4"), ("5", "5"), ("6", "6")],
            [("7", "7"), ("8", "8"), ("9", "9")],
            [("*", "*"), ("0", "0"), ("#", "#")],
        ]
        self.soft_buttons = {}
        for r, row in enumerate(keys):
            for c, (label, key) in enumerate(row):
                if key is None:
                    continue
                b = tk.Label(pad, text=label, width=8, height=1, bg=BODY_KEY, fg=BODY_TEXT,
                             font=("Helvetica", 11, "bold"), relief="flat", padx=6, pady=5,
                             cursor="hand2")
                b.grid(row=r, column=c, padx=4, pady=3, sticky="nsew")
                b.bind("<ButtonPress-1>", lambda e, k=key, w=b: self._vk_down(k, w))
                b.bind("<ButtonRelease-1>", lambda e, k=key, w=b: self._vk_up(k, w))
                if key in ("SOFT1", "SOFT2"):
                    self.soft_buttons[key] = b
            if r == 2:
                tk.Frame(pad, height=6, bg=BODY).grid(row=r, column=0)

        self.status = tk.Label(self, text="", anchor="w", bg="#1b1e23", fg="#aab2bf",
                               font=("Helvetica", 9), padx=8, pady=4)
        self.status.pack(fill="x", side="bottom")

    def _build_menu(self):
        m = tk.Menu(self)
        f = tk.Menu(m, tearoff=0)
        f.add_command(label="New", accelerator="Ctrl+N", command=self.new_tune)
        f.add_command(label="Open…", accelerator="Ctrl+O", command=self.open_file)
        f.add_command(label="Save", accelerator="Ctrl+S", command=self.save_file)
        f.add_command(label="Save As…", command=lambda: self.save_file(ask=True))
        f.add_separator()
        f.add_command(label="Save to phone slot…", command=self.menu_save)
        f.add_command(label="Load from phone slot…", command=self.menu_load)
        f.add_separator()
        f.add_command(label="Import Nokia ringtone (.ott)…", command=self.import_ott)
        f.add_command(label="Export Nokia ringtone (.ott)…", command=self.export_ott)
        f.add_command(label="Export RTTTL…", command=self.export_rtttl)
        f.add_command(label="Export WAV…", command=self.export_wav)
        f.add_command(label="Copy Smart Messaging hex", command=self.copy_hex)
        f.add_separator()
        f.add_command(label="Quit", accelerator="Ctrl+Q", command=self.quit_app)
        m.add_cascade(label="File", menu=f)

        e = tk.Menu(m, tearoff=0)
        e.add_command(label="Title…", command=self.edit_title)
        e.add_command(label="Tempo…", command=self.edit_tempo)
        e.add_separator()
        e.add_command(label="Duration…", accelerator="Enter", command=lambda: self.cmd("Duration"))
        e.add_command(label="Insert", accelerator="Ins", command=lambda: self.cmd("Insert"))
        e.add_command(label="Delete", accelerator="Del", command=lambda: self.cmd("Delete"))
        e.add_command(label="Clear (backspace)", accelerator="Backspace", command=lambda: self.cmd("Clear"))
        e.add_separator()
        e.add_command(label="Toggle treble/bass clef", command=self.toggle_clef)
        e.add_command(label="Toggle sharps/flats", command=self.toggle_sharp)
        m.add_cascade(label="Edit", menu=e)

        p = tk.Menu(m, tearoff=0)
        p.add_command(label="Play / Stop", accelerator="Space", command=self.toggle_play)
        p.add_checkbutton(label="Play note while editing", variable=self.preview_on)
        m.add_cascade(label="Play", menu=p)

        h = tk.Menu(m, tearoff=0)
        h.add_command(label="Editor keys", command=lambda: self.show_help(HELP_EDITOR))
        h.add_command(label="Duration keys", command=lambda: self.show_help(HELP_DURATION))
        h.add_command(label="About", command=self.about)
        m.add_cascade(label="Help", menu=h)
        self.config(menu=m)

    # ------------------------------------------------------------------
    # Keys: keyboard and on-screen keypad share the same hold logic
    # ------------------------------------------------------------------
    def _bind_keys(self):
        self.bind("<KeyPress>", self._on_key_press)
        self.bind("<KeyRelease>", self._on_key_release)
        self.bind("<Control-n>", lambda e: self.new_tune())
        self.bind("<Control-o>", lambda e: self.open_file())
        self.bind("<Control-s>", lambda e: self.save_file())
        self.bind("<Control-q>", lambda e: self.quit_app())

    @staticmethod
    def _map_key(e):
        named = {"Up": "UP", "Down": "DOWN", "Left": "LEFT", "Right": "RIGHT",
                 "Return": "FIRE", "KP_Enter": "FIRE", "F1": "SOFT1", "F2": "SOFT2",
                 "Escape": "BACK", "KP_Multiply": "*", "KP_Divide": "#",
                 "asterisk": "*", "numbersign": "#"}
        if e.keysym in named:
            return named[e.keysym]
        if e.keysym.startswith("KP_") and e.keysym[3:].isdigit():
            return e.keysym[3:]
        if e.char and e.char in "0123456789*#":
            return e.char
        return None

    def _desktop_shortcut(self, e) -> bool:
        if e.state & 0x4:        # Control: leave to the menu accelerators
            return False
        if e.keysym == "space":
            self.toggle_play()
        elif self.screen == "editor" and e.keysym == "Insert":
            self.cmd("Insert")
        elif self.screen == "editor" and e.keysym == "Delete":
            self.cmd("Delete")
        elif self.screen == "editor" and e.keysym == "BackSpace":
            self.cmd("Clear")
        else:
            return False
        return True

    def _on_key_press(self, e):
        key = self._map_key(e)
        if key is None:
            self._desktop_shortcut(e)
            return
        tag = "kb:" + key
        job = self._pending_release.pop(tag, None)
        if job:                     # X11 auto-repeat sends release+press pairs
            self.after_cancel(job)
            return
        if tag in self._down:
            return                  # Windows/macOS auto-repeat: hold timer handles it
        self._press(tag, key)

    def _on_key_release(self, e):
        key = self._map_key(e)
        tag = "kb:" + key if key else None
        if tag in self._down:
            self._pending_release[tag] = self.after(40, lambda: self._release(tag))

    def _vk_down(self, key, widget):
        widget.configure(bg=BODY_KEY_ACTIVE)
        self._press("vk:" + key, key)

    def _vk_up(self, key, widget):
        widget.configure(bg=BODY_KEY)
        self._release("vk:" + key)

    def _press(self, tag, key):
        self._down[tag] = self.after(HOLD_MS, lambda: self._hold(tag, key))
        self.key_pressed(key)

    def _release(self, tag):
        self._pending_release.pop(tag, None)
        job = self._down.pop(tag, None)
        if job:
            self.after_cancel(job)

    def _hold(self, tag, key):
        if tag not in self._down:
            return
        self.key_repeated(key)
        if GAME_ACTION.get(key) in NAV_KEYS and self.screen in ("editor", "duration", "list", "help"):
            self._down[tag] = self.after(REPEAT_MS, lambda: self._hold(tag, key))
        else:
            self._down[tag] = None

    # ------------------------------------------------------------------
    # Key dispatch per screen
    # ------------------------------------------------------------------
    def key_pressed(self, key):
        if self.alert:
            self.dismiss_alert()
            return
        ga = GAME_ACTION.get(key)
        if self.screen == "editor":
            if key == "SOFT1":
                self.open_options()
            elif key == "SOFT2":
                self.open_menu()
            elif ga:
                self.editor_action(ga)
        elif self.screen == "duration":
            if key in ("SOFT1",) or ga == "FIRE":
                self.duration_select()
            elif key == "SOFT2":
                self.show_help(HELP_DURATION, back="duration")
            elif key == "BACK":
                self.screen = "editor"
            elif key == "#":
                self.p_directive = (self.p_directive + 1) % 4
            elif key == "*":
                self.p_style = (self.p_style + 1) % 3
            elif ga in NAV_KEYS:
                self.duration_move(ga)
        elif self.screen == "list":
            self.list_key(key, ga)
        elif self.screen == "help":
            if key in ("SOFT2", "BACK", "SOFT1") or ga == "FIRE":
                self.screen = self.help_state["back"]
            elif ga in ("UP", "DOWN"):
                self.help_scroll(-1 if ga == "UP" else 1)
        self.refresh()

    def key_repeated(self, key):
        """Editor.keyRepeated: hold actions, plus repeating arrows."""
        ga = GAME_ACTION.get(key)
        if self.screen == "editor":
            if ga in NAV_KEYS:
                self.editor_action(ga)
            elif key == "1":
                self.rt.set_index(0)
                self.after_move()
            elif key == "7":
                self.rt.set_index(0 if self.rt.is_empty() else min(SIZE - 1, self.rt.last_index() + 1))
                self.after_move()
            elif key == "0":
                self.cmd("Insert")
            elif key == "*":
                self.toggle_clef()
            elif key == "#":
                self.toggle_sharp()
        elif self.screen in ("duration",) and ga in NAV_KEYS:
            self.duration_move(ga)
        elif self.screen == "list" and ga in ("UP", "DOWN"):
            self.list_key(key, ga)
        elif self.screen == "help" and ga in ("UP", "DOWN"):
            self.help_scroll(-1 if ga == "UP" else 1)
        self.refresh()

    # ------------------------------------------------------------------
    # Editor behaviour (Editor.directionKeyAction / commandAction)
    # ------------------------------------------------------------------
    def editor_action(self, ga):
        rt = self.rt
        i = rt.index
        if ga == "FIRE":
            self.stop_play()
            self.open_duration()
        elif ga == "RIGHT":
            if rt.get(i)[0] != -1 or rt.get(i + 1)[0] != -1:
                self.change_index(+1)
        elif ga == "LEFT":
            self.change_index(-1)
        elif ga == "UP":
            self.change_note(+1)
        elif ga == "DOWN":
            self.change_note(-1)

    def change_index(self, delta):
        self.rt.set_index(self.rt.index + delta)
        self.rt.trim()
        self.after_move()

    def after_move(self):
        self.preview_note()

    def change_note(self, delta):
        i = self.rt.index
        n = self.rt.get(i)[2]
        if n <= 0:
            return
        m = n + delta
        if NOTE_MIN <= m <= NOTE_MAX:
            self.stop_play()
            self.rt.set(i, note=m)
            self.touch()
        self.preview_note()

    def cmd(self, name):
        rt = self.rt
        if name == "Duration":
            self.stop_play()
            self.open_duration()
        elif name == "Insert":
            if rt.get(SIZE - 1)[0] != -1:
                self.show_alert("Ringtone is full\n(128 notes)")
            else:
                rt.insert(rt.index)
                self.touch()
        elif name == "Delete":
            rt.delete(rt.index)
            self.touch()
        elif name == "Clear":               # the original Clear works like backspace
            if rt.index > 0:
                rt.index -= 1
                rt.delete(rt.index)
                self.touch()
        elif name in ("Play", "Stop"):
            self.toggle_play()
        elif name == "More":
            self.open_menu()
            return
        elif name == "Help":
            self.show_help(HELP_EDITOR)
            return
        self.screen = "editor"
        self.refresh()

    def toggle_clef(self):
        self.treble = not self.treble
        self.refresh()

    def toggle_sharp(self):
        self.sharp = not self.sharp
        self.refresh()

    # ------------------------------------------------------------------
    # Duration picker (DurationEdit)
    # ------------------------------------------------------------------
    def open_duration(self):
        rt = self.rt
        i = rt.index
        d, dr, n, s = rt.get(i)
        if n < 0:
            d, _x, n, _y = rt.get(i - 1)
        if 0 <= d < 6:
            self.px = d
        self.py = 1 if n > 0 else 0
        if dr < 0:
            dr = rt.get(i - 1)[1]
        if s < 0:
            s = rt.get(i - 1)[3]
        self.p_directive = max(0, dr)
        self.p_style = max(0, s)
        self.screen = "duration"
        self.refresh()

    def duration_move(self, ga):
        dx, dy = {"LEFT": (-1, 0), "RIGHT": (1, 0), "UP": (0, -1), "DOWN": (0, 1)}[ga]
        if 0 <= self.px + dx < 6:
            self.px += dx
        if 0 <= self.py + dy < 2:
            self.py += dy

    def duration_select(self):
        rt = self.rt
        i = rt.index
        n = rt.get(i)[2]
        if n <= 0:
            n = rt.get(i - 1)[2]
            if n <= 0:
                n = NOTE_DEFAULT
        rt.set(i, self.px, self.p_directive, n * self.py, self.p_style)
        self.touch()
        self.screen = "editor"
        self.preview_note()

    # ------------------------------------------------------------------
    # Lists: Options, Menu, Save/Load slots
    # ------------------------------------------------------------------
    def open_list(self, title, items, on_select, back="editor", soft=("Select", "Back")):
        self.list_state = {"title": title, "items": items, "sel": 0, "top": 0,
                           "on_select": on_select, "back": back, "soft": soft}
        self.screen = "list"
        self.refresh()

    def list_key(self, key, ga):
        st = self.list_state
        if key in ("SOFT2", "BACK"):
            self.screen = st["back"]
        elif key == "SOFT1" or ga == "FIRE":
            st["on_select"](st["sel"])
        elif ga == "UP":
            st["sel"] = (st["sel"] - 1) % len(st["items"])
        elif ga == "DOWN":
            st["sel"] = (st["sel"] + 1) % len(st["items"])

    def open_options(self):
        items = ["Duration", "Insert", "Delete", "Clear",
                 "Stop" if self.playing else "Play", "More", "Help"]
        self.open_list("Options", items, lambda k: self.cmd(items[k]))

    def open_menu(self):
        items = ["Title", "Tempo", "Save", "Load"]

        def pick(k):
            self.screen = "editor"
            [self.edit_title, self.edit_tempo, self.menu_save, self.menu_load][k]()

        self.open_list("Menu", items, pick, soft=("Select", "Back"))

    def slot_titles(self):
        titles = []
        for rec in self.records:
            titles.append(rec.split(";", 1)[0] or "Untitled")
        return titles

    def menu_save(self):
        items = self.slot_titles() + ["-Empty-"]

        def pick(k):
            rec = self.rt.to_record()
            if k < len(self.records):
                self.records[k] = rec
            else:
                self.records.append(rec)
            try:
                save_slots(self.records)
                self.screen = "editor"
                self.show_alert("Saved")
            except OSError:
                self.screen = "editor"
                self.show_alert("Not saved")

        self.open_list("Save", items, pick, back="editor")

    def menu_load(self):
        if not self.records:
            self.screen = "editor"
            self.show_alert("Nothing saved yet")
            return

        def pick(k):
            if not self.confirm_discard():
                return
            try:
                self.rt = Ringtone.from_record(self.records[k])
            except ValueError:
                self.show_alert("Record is damaged")
                return
            self.start = 0
            self.path = None
            self.dirty = False
            self.screen = "editor"
            self.refresh()

        self.open_list("Load", self.slot_titles(), pick, back="editor")

    # ------------------------------------------------------------------
    # Help and alerts
    # ------------------------------------------------------------------
    def show_help(self, text, back=None):
        self.stop_play()
        self.help_state = {"lines": text.split("\n"), "top": 0,
                           "back": back or ("editor" if self.screen in ("list", "help") else self.screen)}
        self.screen = "help"
        self.refresh()

    def help_scroll(self, d):
        st = self.help_state
        visible = (LH - 18) // 11
        st["top"] = max(0, min(len(st["lines"]) - visible, st["top"] + d))

    def show_alert(self, text, ms=1400):
        self.alert = text
        if self.alert_job:
            self.after_cancel(self.alert_job)
        self.alert_job = self.after(ms, self.dismiss_alert)
        self.refresh()

    def dismiss_alert(self):
        self.alert = None
        if self.alert_job:
            self.after_cancel(self.alert_job)
            self.alert_job = None
        self.refresh()

    # ------------------------------------------------------------------
    # Title / tempo
    # ------------------------------------------------------------------
    def edit_title(self):
        value = simpledialog.askstring("Title", f"Title (up to {TITLE_MAX} characters):",
                                       initialvalue=self.rt.title, parent=self)
        if value is not None:
            value = value.replace(";", ",").strip()[:TITLE_MAX]
            self.rt.title = value or "Untitled"
            self.touch()
        self.screen = "editor"
        self.refresh()

    def edit_tempo(self):
        value = simpledialog.askinteger(
            "Tempo", "Tempo in beats per minute (25–900).\n"
            "Phones play the next value up in the Smart Messaging table.",
            initialvalue=self.rt.tempo, minvalue=25, maxvalue=900, parent=self)
        if value:
            self.rt.tempo = value
            self.touch()
        self.screen = "editor"
        self.refresh()

    # ------------------------------------------------------------------
    # Sound
    # ------------------------------------------------------------------
    def preview_note(self):
        """Editor.paint plays the note under the cursor after every move."""
        d, dr, n, s = self.rt.get(self.rt.index)
        if n < 0 or self.playing:
            self.preview_until = 0
            return
        self.preview_until = time.monotonic() + 0.8
        if n > 0 and self.preview_on.get():
            wav = pcm_to_wav(_square(note_freq(n), 0.3))
            self.audio.play(wav, 0.3)

    def toggle_play(self):
        if self.playing:
            self.stop_play()
        else:
            self.start_play()
        self.refresh()

    def start_play(self):
        if self.rt.is_empty():
            self.show_alert("Nothing to play")
            return
        wav, self.timeline = render_tune(self.rt)
        length = self.timeline[-1][1] if self.timeline else 0
        if not self.audio.play(wav, length):
            self.show_alert("No audio player found\nUse File > Export WAV")
        self.playing = True
        self.play_t0 = time.monotonic()
        self.play_index = -1
        self._play_tick()

    def _play_tick(self):
        if not self.playing:
            return
        t = time.monotonic() - self.play_t0
        if not self.timeline or t >= self.timeline[-1][1]:
            self.stop_play()
            self.refresh()
            return
        for t0, t1, idx in self.timeline:
            if t0 <= t < t1:
                if idx != self.play_index:
                    self.play_index = idx
                    self.refresh()
                break
        self.play_job = self.after(30, self._play_tick)

    def stop_play(self):
        if self.playing:
            self.audio.stop()
        self.playing = False
        self.play_index = -1
        if self.play_job:
            self.after_cancel(self.play_job)
            self.play_job = None

    def _tick(self):
        # refresh the header: E: counter while playing, N: label timing out
        if self.playing or (self.preview_until and time.monotonic() > self.preview_until):
            if not self.playing:
                self.preview_until = 0
            self.refresh()
        self.after(250, self._tick)

    # ------------------------------------------------------------------
    # Mouse
    # ------------------------------------------------------------------
    def _on_click(self, e):
        s = self.S
        x, y = e.x / s, e.y / s
        if y >= LH:                                     # soft-key strip
            self.key_pressed("SOFT1" if x < LW / 2 else "SOFT2")
            return
        if self.alert:
            self.dismiss_alert()
            return
        if self.screen == "editor":
            for idx, nx in self._visible_notes():
                filled = self.rt.get(idx)[0] != -1
                if abs(x - nx) <= 11 and (filled or idx == self.rt.last_index() + 1):
                    if idx != self.rt.index:
                        self.rt.set_index(idx)
                        self.rt.trim()
                        self.preview_note()
                        self.refresh()
                    return
        elif self.screen == "duration":
            tx, ty = (LW - 96) // 2, LH // 2 - 47
            cx, cy = int((x - tx) // 16), int((y - ty) // 47)
            if 0 <= cx < 6 and 0 <= cy < 2:
                if (cx, cy) == (self.px, self.py):
                    self.duration_select()
                else:
                    self.px, self.py = cx, cy
                self.refresh()
        elif self.screen == "list":
            st = self.list_state
            row = int((y - 18) // ROW_H)
            k = st["top"] + row
            if 0 <= row and k < len(st["items"]):
                if k == st["sel"]:
                    st["on_select"](k)
                else:
                    st["sel"] = k
                self.refresh()

    def _on_double_click(self, e):
        if self.screen == "editor" and e.y / self.S < LH:
            self.open_duration()

    def _on_wheel(self, e):
        self._wheel(1 if e.delta > 0 else -1)

    def _wheel(self, d):
        if self.screen == "editor":
            self.change_note(d)
        elif self.screen == "list":
            self.list_key("", "UP" if d > 0 else "DOWN")
        elif self.screen == "help":
            self.help_scroll(-d)
        self.refresh()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def L(self, *v):
        return [a * self.S for a in v]

    def text(self, x, y, txt, anchor="nw", font=None, fill="#000"):
        self.canvas.create_text(x * self.S, y * self.S, text=txt, anchor=anchor,
                                font=font or self.font_small, fill=fill)

    def rect(self, x, y, w, h, fill="#000", outline=""):
        self.canvas.create_rectangle(*self.L(x, y, x + w, y + h), fill=fill, outline=outline)

    def refresh(self):
        c = self.canvas
        c.delete("all")
        c.create_rectangle(0, 0, LW * self.S, (LH + SOFT_H) * self.S, fill=LCD_BG, outline="")
        if self.screen == "editor":
            self.draw_editor()
            soft = ("Options", "Menu")
        elif self.screen == "duration":
            self.draw_duration()
            soft = ("Select", "Help")
        elif self.screen == "list":
            self.draw_list()
            soft = self.list_state["soft"]
        else:
            self.draw_help()
            soft = ("", "Back")
        # soft-key strip
        c.create_line(*self.L(0, LH, LW, LH), fill="#000")
        self.text(3, LH + SOFT_H / 2, soft[0], anchor="w", font=self.font_soft)
        self.text(LW - 3, LH + SOFT_H / 2, soft[1], anchor="e", font=self.font_soft)
        for key, label in zip(("SOFT1", "SOFT2"), soft):
            if key in self.soft_buttons:
                self.soft_buttons[key].configure(text=label or " ")
        if self.alert:
            self.draw_alert()
        self.update_status()

    def _visible_notes(self):
        """Return [(index, x)] for the notes on screen (Editor.drawManyNotes)."""
        count = (LW - 10) // 23
        focus = self.play_index if self.playing and self.play_index >= 0 else self.rt.index
        if focus < self.start:
            self.start = focus
        visible = count - 1 if self.start == 0 else count
        if focus >= self.start + visible:
            self.start = max(1, focus - count + 1)
        offset, n = 10, count
        if self.start == 0:
            n -= 1
            offset += 16
        return [(self.start + k, 23 * k + offset) for k in range(n) if self.start + k < SIZE]

    def draw_editor(self):
        c, rt = self.canvas, self.rt
        base = LH - 36                       # middle staff line
        # grey guide lines above/below and the black five-line staff
        y = LH
        for i in range(12):
            y -= 6
            if y <= FONT_H:
                break
            c.create_line(*self.L(0, y, LW, y), fill="#000" if 3 <= i < 8 else LCD_GUIDE,
                          width=max(1, self.S // 2))
        notes = self._visible_notes()
        if self.start == 0:
            c.create_image(0, (base - 24) * self.S, image=self.img_clef[0 if self.treble else 1], anchor="nw")
        for idx, x in notes:
            if self.playing and idx == self.play_index:
                self.rect(x - 9, FONT_H + 1, 20, LH - FONT_H - 2, fill="#dce8fb")
            self.draw_note(idx, x, base)
            if idx == rt.index:
                c.create_line(*self.L(x - 3, FONT_H, x - 3, LH), fill=RED,
                              dash=(2 * self.S, 2 * self.S), width=max(2, self.S - 1))
        # header (Editor.paint)
        now = time.monotonic()
        if self.playing:
            head = f"E:{int(now - self.play_t0)}"
        elif self.preview_until and now <= self.preview_until:
            d, dr, n, s = rt.get(rt.index)
            head = "N:" + note_label(d, dr, n, self.sharp)
        else:
            head = rt.title
        self.rect(0, 0, LW, FONT_H, fill=LCD_BG)
        self.text(1, 0, head)
        last = rt.last_index() + 1 if not rt.is_empty() else 1
        self.text(LW - 1, 0, f"T:{rt.tempo} {rt.index + 1}/{max(last, rt.index + 1)}", anchor="ne")

    def anchor_y(self, o):
        return 11 + (13, 20, 3)[o]

    def draw_note(self, idx, x, base):
        d, dr, n, s = self.rt.get(idx)
        if d < 0:
            return
        y, o = base, 0
        if n > 0:
            octave, semi = (n - 1) // 12, (n - 1) % 12
            y = base + (60 if self.treble else 66) - octave * 21
            y -= 3 * (STEPS_SHARP if self.sharp else STEPS_FLAT)[semi]
            if semi in ACCIDENTAL_SEMITONES:
                self.canvas.create_image((x - 3 - 7) * self.S, (y - 5) * self.S,
                                         image=self.img_acc[0 if self.sharp else 1], anchor="nw")
            o = 1 if y > base else 2
        self.draw_glyph(x - 3, y - self.anchor_y(o), d, o, max(0, dr), max(0, s))

    def draw_glyph(self, xl, yt, d, o, directive, style):
        """Img.getNotes: a 16 x 48 cell with the sprite and its marks."""
        self.canvas.create_image(xl * self.S, (yt + 11) * self.S, image=self.img_notes[d][o], anchor="nw")
        ay = self.anchor_y(o)
        if directive in (1, 2):
            self.rect(xl + 11, yt + ay - 3, 2, 2)
        if directive == 2:
            self.rect(xl + 14, yt + ay - 3, 2, 2)
        if directive == 3:
            y6 = {0: ay + 12, 1: ay + 5, 2: ay - 3 - FONT_H}[o]
            self.text(xl + 3, yt + y6, "3")
        if style and o:
            y6 = ay + 5 if o == 1 else ay - 6
            if style == 1:
                self.rect(xl + 1, yt + y6, 8, 2)      # continuous: a bar
            else:
                self.rect(xl + 3, yt + y6, 3, 2)      # staccato: a dot

    def draw_duration(self):
        tx, ty = (LW - 96) // 2, LH // 2 - 47
        for x in range(6):
            for y in range(2):
                self.draw_glyph(tx + 16 * x, ty + 47 * y, x, y, self.p_directive, self.p_style)
        self.canvas.create_rectangle(*self.L(tx + 16 * self.px, ty + 47 * self.py,
                                             tx + 16 * self.px + 16, ty + 47 * self.py + 47),
                                     outline=RED, width=max(1, self.S // 2 + 1))
        what = "rest" if self.py == 0 else "note"
        desc = f"{DURATION_NAMES[self.px]} {what}"
        if self.p_directive:
            desc += f", {DIRECTIVE_NAMES[self.p_directive]}"
        if self.p_style and self.py:
            desc += f", {STYLE_NAMES[self.p_style]}"
        self.text(LW / 2, 1, desc, anchor="n")

    def draw_list(self):
        st = self.list_state
        self.text(LW / 2, 1, st["title"], anchor="n", font=self.font_list_b)
        self.canvas.create_line(*self.L(0, 16, LW, 16), fill="#000")
        rows = (LH - 20) // ROW_H
        if st["sel"] < st["top"]:
            st["top"] = st["sel"]
        if st["sel"] >= st["top"] + rows:
            st["top"] = st["sel"] - rows + 1
        for r in range(rows):
            k = st["top"] + r
            if k >= len(st["items"]):
                break
            y = 18 + ROW_H * r
            sel = k == st["sel"]
            if sel:
                self.rect(0, y, LW, ROW_H, fill="#000")
            self.text(6, y + ROW_H / 2, f"{k + 1}. {st['items'][k]}", anchor="w",
                      font=self.font_list, fill="#fff" if sel else "#000")

    def draw_help(self):
        st = self.help_state
        self.text(LW / 2, 1, "Help", anchor="n", font=self.font_list_b)
        self.canvas.create_line(*self.L(0, 16, LW, 16), fill="#000")
        visible = (LH - 18) // 11
        for r, line in enumerate(st["lines"][st["top"]:st["top"] + visible]):
            self.text(4, 18 + 11 * r, line, font=self.font_help)
        if len(st["lines"]) > visible:
            frac = st["top"] / max(1, len(st["lines"]) - visible)
            self.rect(LW - 3, 18 + frac * (LH - 32), 2, 12)

    def draw_alert(self):
        lines = self.alert.split("\n")
        h = 14 + 12 * len(lines)
        y0 = (LH - h) / 2
        self.rect(16, y0, LW - 32, h, fill="#fff", outline="#000")
        for k, line in enumerate(lines):
            self.text(LW / 2, y0 + 7 + 12 * k, line, anchor="n", font=self.font_list)

    def update_status(self):
        rt = self.rt
        n = rt.count()
        size = len(encode_ott(rt))
        fit = "fits in 1 SMS" if size <= SMS_PAYLOAD else "needs 2+ SMS"
        tempo = f"tempo {rt.tempo}"
        if play_bpm(rt.tempo) != rt.tempo:
            tempo += f" (plays at {play_bpm(rt.tempo)})"
        audio = "" if self.audio.available else " · no audio player found"
        name = os.path.basename(self.path) if self.path else "not saved to a file"
        self.status.configure(
            text=f"{n}/{SIZE} notes · {tempo} · ringtone {size} bytes, {fit} · {name}{audio}")
        mark = "*" if self.dirty else ""
        self.title(f"{mark}{rt.title} — {APP_NAME}")

    # ------------------------------------------------------------------
    # Files
    # ------------------------------------------------------------------
    def touch(self):
        self.dirty = True

    def confirm_discard(self) -> bool:
        if not self.dirty or self.rt.is_empty():
            return True
        return messagebox.askyesno(APP_NAME, "Discard the changes to this ringtone?", parent=self)

    def new_tune(self):
        if not self.confirm_discard():
            return
        self.stop_play()
        self.rt = Ringtone()
        self.start = 0
        self.path = None
        self.dirty = False
        self.screen = "editor"
        self.refresh()

    def open_file(self):
        if not self.confirm_discard():
            return
        path = filedialog.askopenfilename(
            parent=self, title="Open ringtone",
            filetypes=[("MeloCreate ringtone", "*.mcr"), ("Nokia ringtone", "*.ott"), ("All files", "*.*")])
        if path:
            self.open_path(path)

    def open_path(self, path):
        try:
            if path.lower().endswith(".ott"):
                with open(path, "rb") as f:
                    rt = decode_ott(f.read())
                self.path = None
            else:
                with open(path, encoding="utf-8") as f:
                    rt = Ringtone.from_record(f.read())
                self.path = path
        except (OSError, ValueError, IndexError) as exc:
            messagebox.showerror(APP_NAME, f"Could not open {os.path.basename(path)}:\n{exc}", parent=self)
            return
        self.stop_play()
        self.rt = rt
        self.start = 0
        self.dirty = False
        self.screen = "editor"
        self.refresh()

    def save_file(self, ask=False):
        path = self.path
        if ask or not path:
            path = filedialog.asksaveasfilename(
                parent=self, title="Save ringtone", defaultextension=".mcr",
                initialfile=f"{self.rt.title}.mcr",
                filetypes=[("MeloCreate ringtone", "*.mcr"), ("All files", "*.*")])
            if not path:
                return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.rt.to_record() + "\n")
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Could not save:\n{exc}", parent=self)
            return
        self.path = path
        self.dirty = False
        self.refresh()

    def _export(self, title, ext, kind, writer):
        if self.rt.is_empty():
            messagebox.showinfo(APP_NAME, "The ringtone is empty.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            parent=self, title=title, defaultextension=ext, initialfile=f"{self.rt.title}{ext}",
            filetypes=[(kind, f"*{ext}"), ("All files", "*.*")])
        if not path:
            return
        try:
            writer(path)
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Could not export:\n{exc}", parent=self)

    def export_ott(self):
        def write(path):
            with open(path, "wb") as f:
                f.write(encode_ott(self.rt))
        self._export("Export Nokia ringtone", ".ott", "Nokia ringtone", write)

    def export_rtttl(self):
        def write(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(to_rtttl(self.rt) + "\n")
        lossy = any(dr in (2, 3) for _i, _d, dr, _n, _s in self.rt.entries())
        self._export("Export RTTTL", ".txt", "RTTTL text", write)
        if lossy:
            messagebox.showinfo(APP_NAME, "RTTTL has no triplets or double dots, so those notes "
                                "were written as plain or single-dotted notes.", parent=self)

    def export_wav(self):
        def write(path):
            wav, _t = render_tune(self.rt)
            with open(path, "wb") as f:
                f.write(wav)
        self._export("Export WAV", ".wav", "WAV audio", write)

    def import_ott(self):
        if not self.confirm_discard():
            return
        path = filedialog.askopenfilename(parent=self, title="Import Nokia ringtone",
                                          filetypes=[("Nokia ringtone", "*.ott"), ("All files", "*.*")])
        if path:
            self.open_path(path)

    def copy_hex(self):
        data = encode_ott(self.rt)
        self.clipboard_clear()
        self.clipboard_append(data.hex().upper())
        self.show_alert(f"Copied {len(data)} bytes\nas hex")

    def about(self):
        messagebox.showinfo(
            APP_NAME,
            f"{APP_NAME} {VERSION} (desktop)\n\n"
            "A Python/Tkinter recreation of MeloCreate, the ringtone composer\n"
            "for Nokia Series 40 phones by Alan Ong (2003).\n\n"
            f"Audio: {self.audio.name}\nPhone slots: {slots_path()}", parent=self)

    def quit_app(self):
        if not self.confirm_discard():
            return
        self.stop_play()
        self.audio.close()
        self.destroy()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    scale = 3
    path = None
    while argv:
        arg = argv.pop(0)
        if arg in ("-z", "--zoom") and argv:
            scale = max(1, min(6, int(argv.pop(0))))
        elif arg in ("-h", "--help"):
            print("usage: melocreate.py [--zoom 1-6] [file.mcr|file.ott]")
            return 0
        else:
            path = arg
    app = MeloCreate(scale=scale, path=path)
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
