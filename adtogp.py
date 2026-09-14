#!/usr/bin/env python3
"""
MusicXML + MIDI Drum Remapper for Guitar Pro 8

- MusicXML: frets / instruments / visuals / dynamics → mf
- MIDI (.mid/.midi): все note velocity → mf (по умолчанию 85)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import mido
except ImportError:
    mido = None

DEFAULT_FRETS: Dict[int, int] = {49: 42}
DEFAULT_INSTRUMENTS: Dict[str, str] = {"P1-I23": "P1-I4"}
DEFAULT_FRET_INSTRUMENTS: Dict[int, str] = {}
DEFAULT_REMOVE_FRETS: List[int] = []

DEFAULT_VISUALS: Dict[str, Tuple[str, str, str]] = {
    "P1-I4":  ("G", "5", "x"),
    "P1-I5":  ("G", "5", "x"),
    "P1-I6":  ("A", "5", "x"),
    "P1-I7":  ("F", "5", "x"),
    "P1-I1":  ("C", "5", "normal"),
    "P1-I2":  ("C", "5", "x"),
    "P1-I10": ("G", "4", "normal"),
    "P1-I11": ("D", "5", "normal"),
    "P1-I12": ("E", "5", "normal"),
    "P1-I13": ("F", "4", "normal"),
    "P1-I16": ("F", "5", "x"),
    "P1-I17": ("F", "5", "x"),
    "P1-I23": ("A", "5", "x"),
    "P1-I19": ("A", "5", "x"),
    "P1-I57": ("C", "5", "triangle"),
    "P1-I93": ("A", "5", "x"),
}

OUTPUT_SUFFIX = "_remapped"
CONFIG_NAME = "config.json"
FORCE_DYNAMICS = "mf"
MIDI_MF_VELOCITY = 80  # типичное значение для mf (0–127)


def find_config() -> Optional[Path]:
    script_dir = Path(__file__).parent
    for path in (script_dir / CONFIG_NAME, Path.cwd() / CONFIG_NAME):
        if path.exists():
            return path
    return None


def load_config(config_path: Optional[Path] = None):
    frets = DEFAULT_FRETS.copy()
    instruments = DEFAULT_INSTRUMENTS.copy()
    visuals = DEFAULT_VISUALS.copy()
    remove_frets = DEFAULT_REMOVE_FRETS.copy()
    fret_instruments: Dict[int, str] = DEFAULT_FRET_INSTRUMENTS.copy()
    midi_velocity = MIDI_MF_VELOCITY

    if config_path is None:
        config_path = find_config()

    if config_path and config_path.exists():
        print(f"Конфиг: {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "frets" in data:
            frets = {int(k): int(v) for k, v in data["frets"].items()}
        if "instruments" in data:
            instruments = data["instruments"]
        if "visuals" in data:
            for k, v in data["visuals"].items():
                visuals[k] = tuple(v)
        if "remove_frets" in data:
            remove_frets = [int(x) for x in data["remove_frets"]]
        if "fret_instruments" in data:
            fret_instruments = {int(k): v for k, v in data["fret_instruments"].items()}
        if "midi_mf_velocity" in data:
            midi_velocity = int(data["midi_mf_velocity"])
    else:
        print("Конфиг не найден — значения по умолчанию")

    return frets, instruments, visuals, remove_frets, fret_instruments, midi_velocity


# ─── MusicXML ───────────────────────────────────────────────────────────────

def force_dynamics(content: str, target: str = "mf") -> str:
    pattern = re.compile(
        r"(<dynamics[^>]*>)\s*(?:<[^/>]+/>\s*)+(</dynamics>)",
        re.IGNORECASE | re.DOTALL,
    )
    new_dyn = f"<dynamics>\n      <{target}/>\n     </dynamics>"
    count = len(pattern.findall(content))
    content = pattern.sub(new_dyn, content)
    print(f"  dynamics → {target}   ({count} шт.)")
    return content


def remove_notes_by_fret(content: str, frets_to_remove: List[int]) -> str:
    if not frets_to_remove:
        return content
    total = 0

    def maybe_remove(match: re.Match) -> str:
        nonlocal total
        note = match.group(0)
        for f in frets_to_remove:
            if f"<fret>{f}</fret>" in note:
                total += 1
                return ""
        return note

    content = re.sub(r"<note\b[^>]*>.*?</note>", maybe_remove, content, flags=re.DOTALL)
    content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)
    print(f"  remove frets {frets_to_remove}   ({total} нот удалено)")
    return content


def remap_frets(content: str, frets: Dict[int, int]) -> str:
    if not frets:
        return content
    tmp_map = {}
    for i, (old, new) in enumerate(frets.items()):
        marker = f"__TMPFRET_{i}__"
        old_tag = f"<fret>{old}</fret>"
        count = content.count(old_tag)
        if count:
            content = content.replace(old_tag, f"<fret>{marker}</fret>")
            tmp_map[marker] = new
            print(f"  frets: {old} → {new}   ({count} шт.)")
    for marker, new in tmp_map.items():
        content = content.replace(f"<fret>{marker}</fret>", f"<fret>{new}</fret>")
    return content


def remap_instruments_in_notes(
    content: str,
    instruments: Dict[str, str],
    fret_instruments: Dict[int, str],
) -> str:
    total = 0

    def fix_note(match: re.Match) -> str:
        nonlocal total
        note = match.group(0)

        for old_id, new_id in instruments.items():
            pattern = re.compile(rf'(<instrument\s+id=["\']){re.escape(old_id)}(["\'])')
            note, n = pattern.subn(rf'\1{new_id}\2', note)
            total += n

        m_fret = re.search(r"<fret>(\d+)</fret>", note)
        if m_fret:
            f = int(m_fret.group(1))
            if f in fret_instruments:
                new_id = fret_instruments[f]
                note2, n = re.subn(
                    r'(<instrument\s+id=["\'])P1-I\d+(["\'])',
                    rf'\1{new_id}\2',
                    note,
                    count=1,
                )
                if n:
                    note = note2
                    total += n

        return note

    content = re.sub(r"<note\b[^>]*>.*?</note>", fix_note, content, flags=re.DOTALL)
    print(f"  instruments (id + по fret)   ({total} шт.)")
    return content


def apply_visuals(content: str, visuals: Dict[str, Tuple[str, str, str]]) -> str:
    total = 0

    def fix_note(match: re.Match) -> str:
        nonlocal total
        note = match.group(0)
        m_id = re.search(r'<instrument\s+id=["\'](P1-I\d+)["\']', note)
        if not m_id:
            return note
        iid = m_id.group(1)
        if iid not in visuals:
            return note

        step, octave, head = visuals[iid]
        changed = False

        new_note, n = re.subn(
            r"<display-step>[^<]*</display-step>",
            f"<display-step>{step}</display-step>",
            note, count=1,
        )
        if n:
            changed = True
            note = new_note

        new_note, n = re.subn(
            r"<display-octave>[^<]*</display-octave>",
            f"<display-octave>{octave}</display-octave>",
            note, count=1,
        )
        if n:
            changed = True
            note = new_note

        if re.search(r"<notehead>[^<]*</notehead>", note):
            new_note, n = re.subn(
                r"<notehead>[^<]*</notehead>",
                f"<notehead>{head}</notehead>",
                note, count=1,
            )
            if n:
                changed = True
                note = new_note
        else:
            note = re.sub(r"(</stem>)", rf"\1\n    <notehead>{head}</notehead>", note, count=1)
            changed = True

        if changed:
            total += 1
        return note

    content = re.sub(r"<note\b[^>]*>.*?</note>", fix_note, content, flags=re.DOTALL)
    print(f"  visuals (step/octave/notehead)   ({total} нот)")
    return content


def process_musicxml(
    input_path: Path,
    frets, instruments, visuals, remove_frets, fret_instruments,
    suffix: str,
) -> Path:
    print(f"\nЧитаю MusicXML: {input_path}")
    content = input_path.read_text(encoding="utf-8")

    print("Применяю замены:")
    content = remove_notes_by_fret(content, remove_frets)
    content = remap_frets(content, frets)
    content = remap_instruments_in_notes(content, instruments, fret_instruments)
    content = apply_visuals(content, visuals)
    content = force_dynamics(content, FORCE_DYNAMICS)

    output_path = input_path.parent / f"{input_path.stem}{suffix}{input_path.suffix}"
    output_path.write_text(content, encoding="utf-8")
    print(f"\nГотово → {output_path}")
    return output_path


# ─── MIDI ───────────────────────────────────────────────────────────────────

def process_midi(
    input_path: Path,
    velocity: int,
    frets: Dict[int, int],
    remove_frets: List[int],
    suffix: str,
) -> Path:
    if mido is None:
        raise RuntimeError("Библиотека mido не установлена. Установите: pip install mido")

    print(f"\nЧитаю MIDI: {input_path}")
    mid = mido.MidiFile(str(input_path))
    print(f"  format: type {mid.type}, tracks: {len(mid.tracks)}, ticks/beat: {mid.ticks_per_beat}")

    remove_set = set(remove_frets or [])
    pitch_changed = 0
    vel_changed = 0
    note_ons = 0
    removed = 0

    for track in mid.tracks:
        new_msgs = []
        # time в MIDI — delta; при удалении сообщений нужно переносить delta на следующее
        carry_time = 0
        for msg in track:
            if msg.type in ("note_on", "note_off") and msg.note in remove_set:
                # удаляем ноту, delta переносим дальше
                carry_time += msg.time
                removed += 1
                continue

            if carry_time and hasattr(msg, "time"):
                msg = msg.copy(time=msg.time + carry_time)
                carry_time = 0

            if msg.type in ("note_on", "note_off"):
                old_note = msg.note
                if old_note in frets:
                    new_note = frets[old_note]
                    if new_note != old_note:
                        msg = msg.copy(note=new_note)
                        pitch_changed += 1

                if msg.type == "note_on" and msg.velocity > 0:
                    note_ons += 1
                    if msg.velocity != velocity:
                        msg = msg.copy(velocity=velocity)
                        vel_changed += 1

            new_msgs.append(msg)

        # если в конце остался carry_time — добавить к последнему сообщению
        if carry_time and new_msgs:
            last = new_msgs[-1]
            if hasattr(last, "time"):
                new_msgs[-1] = last.copy(time=last.time + carry_time)

        track.clear()
        track.extend(new_msgs)

    output_path = input_path.parent / f"{input_path.stem}{suffix}{input_path.suffix}"
    mid.save(str(output_path))

    print(f"  note_on (после удаления): {note_ons}")
    print(f"  удалено сообщений (note_on/off): {removed}")
    print(f"  pitch (ноты) заменено: {pitch_changed}")
    print(f"  velocity → {velocity}: {vel_changed}")
    print(f"\nГотово → {output_path}")
    return output_path



# ─── CLI ────────────────────────────────────────────────────────────────────

def ask_path() -> Path:
    print("=" * 50)
    print("  MusicXML / MIDI Drum Remapper (Guitar Pro 8)")
    print("=" * 50)
    print()
    while True:
        raw = input("Путь к файлу (.xml / .mid / .midi): ").strip().strip('"').strip("'")
        if not raw:
            print("Путь не может быть пустым.\n")
            continue
        path = Path(raw).expanduser()
        if path.exists():
            return path
        print(f"Файл не найден: {path}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remap drum notes in MusicXML or normalize dynamics in MIDI"
    )
    parser.add_argument("input", type=Path, nargs="?", default=None)
    parser.add_argument("--config", "-c", type=Path, default=None)
    parser.add_argument("--suffix", default=OUTPUT_SUFFIX)
    parser.add_argument(
        "--velocity", type=int, default=None,
        help=f"MIDI velocity for mf (default: {MIDI_MF_VELOCITY})",
    )
    args = parser.parse_args()

    input_path = args.input.expanduser() if args.input else ask_path()
    frets, instruments, visuals, remove_frets, fret_instruments, midi_vel = load_config(args.config)

    if args.velocity is not None:
        midi_vel = args.velocity

    suffix = args.suffix
    ext = input_path.suffix.lower()

    try:
        if ext in (".mid", ".midi"):
            process_midi(input_path, midi_vel, frets, remove_frets, suffix)
        elif ext in (".xml", ".musicxml"):
            process_musicxml(
                input_path, frets, instruments, visuals,
                remove_frets, fret_instruments, suffix,
            )
        else:
            print(f"Неизвестный формат: {ext}. Поддерживаются .xml, .musicxml, .mid, .midi")
            sys.exit(1)
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

    print()
    if sys.stdin.isatty():
        input("Нажмите Enter, чтобы закрыть...")


if __name__ == "__main__":
    main()