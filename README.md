# AD → GP Drum Remapper (`adtogp.py`)

Remap drum notes from **Addictive Drums 2** MIDI/MusicXML exports for use in **Guitar Pro 8**.

[English](#english) · [Русский](#русский)

---

<a id="english"></a>
## English

### Features

**MusicXML** (`.xml`, `.musicxml`)

- Remap note numbers (`frets`)
- Assign Guitar Pro instrument IDs
- Adjust staff position and noteheads
- Set all dynamics to `mf`
- Remove selected notes (e.g. choke articulations)

**MIDI** (`.mid`, `.midi`)

- Remap pitches with the same table as MusicXML
- Set note velocity to a fixed level (default 80)
- Remove selected note numbers

### Requirements

- Python 3.9+
- For MIDI: `pip install mido`

### Project files

| File | Description |
|------|-------------|
| `adtogp.py` | Script |
| `config.json` | Note mapping AD2 → GP8 |

### Usage

```bash
python adtogp.py
python adtogp.py path/to/file.xml
python adtogp.py path/to/file.mid
python adtogp.py file.mid -c config.json --suffix _gp --velocity 80
```

Writes `*_remapped.xml` or `*_remapped.mid` next to the input file. The original is not modified.

### Config keys

| Key | Description |
|-----|-------------|
| `frets` | `source_note → target_note` |
| `fret_instruments` | GP instrument id (`P1-Ixx`) for a target note (MusicXML) |
| `instruments` | Optional remap by original instrument id |
| `remove_frets` | Note numbers to delete |
| `midi_mf_velocity` | MIDI velocity (0–127) |

Keys starting with `_` are comments only and are ignored by the script.

### License

MIT

---

<a id="русский"></a>
## Русский

### Возможности

**MusicXML** (`.xml`, `.musicxml`)

- Замена номеров нот (`frets`)
- Назначение id инструментов Guitar Pro
- Позиция на стане и вид головки ноты
- Динамики → `mf`
- Удаление выбранных нот (например choke)

**MIDI** (`.mid`, `.midi`)

- Та же замена pitch, что и для MusicXML
- Фиксированный velocity (по умолчанию 80)
- Удаление выбранных номеров нот

### Требования

- Python 3.9+
- Для MIDI: `pip install mido`

### Файлы

| Файл | Описание |
|------|----------|
| `adtogp.py` | Скрипт |
| `config.json` | Таблица нот AD2 → GP8 |

### Запуск

```bash
python adtogp.py
python adtogp.py path/to/file.xml
python adtogp.py path/to/file.mid
python adtogp.py file.mid -c config.json --suffix _gp --velocity 80
```

Рядом с исходником создаётся `*_remapped.xml` или `*_remapped.mid`. Исходный файл не перезаписывается.

### Ключи конфига

| Ключ | Описание |
|------|----------|
| `frets` | `исходная_нота → целевая_нота` |
| `fret_instruments` | id инструмента GP (`P1-Ixx`) для целевой ноты (MusicXML) |
| `instruments` | Опционально: замена по исходному id инструмента |
| `remove_frets` | Номера нот для удаления |
| `midi_mf_velocity` | Velocity в MIDI (0–127) |

Поля с `_` в начале — только пояснения, скрипт их не читает.

### Лицензия

MIT
