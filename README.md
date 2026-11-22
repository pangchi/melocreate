# MeloCreate

A ringtone composer for Nokia Series 40 phones, written as a J2ME MIDlet (MIDP 1.0 / CLDC 1.0) in 2002–2003.

MeloCreate lets you write a monophonic ringtone on a music staff right on the phone's screen, play it back, save it on the handset, and send it to another phone as a Nokia Smart Messaging ringtone over SMS.

> This is a historical project. It is kept here as-is, as the compiled MIDlet. The original Java source is not in this repository.

**Try it today** without a phone or emulator: there is a [browser version](web/) (open `web/index.html`) and a [Python desktop version](python/). Both recreate the original editor; neither includes the SMS sending.

---

## Features

- **Staff-based editor.** Notes are drawn on a five-line staff using real note symbols (whole note down to 1/32), with treble and bass clefs and sharp/flat accidentals. Most phone composers of the time used text like `4c2 8#d2` instead.
- **Note editing.** Insert, delete and clear notes, and move a note up or down in pitch. Notes are named C, C#/Db, D … B.
- **Durations and styles.** Each note has a duration, which can be dotted or a triplet. Each note also has a playing style: natural, continuous or staccato. Rests are supported.
- **Playback.** The tune plays through the Nokia UI Sound API (`com.nokia.mid.sound.Sound`), so you can hear it as you compose. On phones without that API, a silent "dummy" player is used, so the editor still works.
- **Title and tempo.** The title can be up to 15 characters. When the tune is played or sent, the tempo is rounded up to the next value in the Smart Messaging BPM table (25, 28, 31, 35, 40 … 900 BPM), so 120 plays at 125.
- **A new note takes its pitch from the previous note.** If there is no previous note, it starts on C.
- **Save and load.** Ringtones are stored in the phone's Record Management System (RMS), in numbered slots. Each slot shows the ringtone's title, or `-Empty-`.
- **Send by SMS.** The ringtone is encoded to the Nokia Smart Messaging binary ringtone format and sent as a hex payload through the Clickatell HTTP SMS gateway. You enter your Clickatell username, API ID and password, plus the recipient's number in international format (`+65…`). The settings are saved on the phone.
  - Up to 128 notes can be stored. Anything longer than about 70 notes needs more than one SMS, and the app warns you that some phones may not accept a multi-part ringtone.

## Keypad controls

The editor is a full-screen canvas driven by the keypad. These controls are taken from the in-app **Help** screen.

### Editor (staff view)

| Action | Key |
|---|---|
| Open the duration picker for the current note | `5` (FIRE) |
| Change the note's pitch | `2` up / `8` down |
| Move between notes | `4` left / `6` right |
| Insert a note | press and hold `0` |
| Toggle sharp / flat | press and hold `#` |
| Toggle treble / bass clef | press and hold `*` |
| Jump to the first / last note | press and hold `1` / `7` |

Soft-key commands: **Duration, Insert, Delete, Clear, Play / Stop, More** (opens the menu) and **Help**.

### Duration picker

| Action | Key |
|---|---|
| Choose a duration (grid of note symbols) | `2` / `4` / `6` / `8` |
| Cycle dotted / triplet | `#` |
| Cycle continuous / staccato | `*` |
| Select and go back to the editor | `5` (FIRE) / Select |

### Menu

`Title` · `Tempo` · `Save` · `Load` · `Send`

## Requirements

- A MIDP 1.0 / CLDC 1.0 phone. The app targets **Nokia Series 40** devices (for example the Nokia 3100, 3300, 6100, 6610 and 7210).
- For playback: the Nokia UI API (`com.nokia.mid.sound`).
- For sending: a GPRS/WAP data connection and a Clickatell account. Sending no longer works today; see the next section.

## Does Send still work?

Almost certainly not, for three separate reasons:

1. **The API is a retired generation.** MeloCreate logs in at `api.clickatell.com/http/auth` with a username, password and API ID, then sends with `api.clickatell.com/http/sendmsg`. That is Clickatell's old *Developer Central* HTTP API. Clickatell's documentation now lists it as archived and only relevant to accounts created before 15 November 2016. New accounts use the *One API* instead (a JSON POST to `platform.clickatell.com/v1/message`, authorised with an API key), which MeloCreate doesn't speak. An old pre-2016 account might still be accepted by the legacy endpoint, but this hasn't been tested and Clickatell gives no shutdown date.
2. **The phone can't get online.** The MIDlet needs a GPRS/WAP data connection. 2G networks have been switched off in Singapore (2017) and in many other countries, so a Series 40 phone of that era has no data connection to make the call.
3. **Modern phones can't receive it.** The SMS is a Nokia Smart Messaging ringtone: binary data with the UDH `06050415810000`, addressed to the phone's ringtone port. Only old Nokia-compatible handsets understood that. A current iPhone or Android phone shows it as junk or drops it.

To get a tune out of MeloCreate today, use the [web](web/) or [Python](python/) recreations. They export the same Smart Messaging bytes as a Nokia `.ott` file, plus RTTTL and WAV.

## Installing and running

### On a real phone
Copy `melocreate.jad` and `melocreate.jar` to the phone with Nokia PC Suite, Bluetooth or infrared, or host both files on a web server and open the `.jad` in the phone's WAP browser (OTA install).

The JAD carries a 2003 self-signed code-signing certificate that has long since expired. If the phone rejects the signature, delete the `MIDlet-Certificate-1-1` and `MIDlet-Jar-RSA-SHA1` lines from the JAD and install it as an unsigned MIDlet.

### In an emulator
- **[J2ME Loader](https://github.com/nikita36078/J2ME-Loader)** (Android): open `melocreate.jar` directly.
- **[FreeJ2ME](https://github.com/hex007/freej2me)** or **[KEmulator](https://github.com/shinovon/KEmulator)** (desktop): load the JAR. KEmulator emulates the Nokia UI API, so playback works there.
- The Nokia Series 40 SDKs and the Sun J2ME Wireless Toolkit can also run it, if you can still find an installer.

## Repository contents

| File | Description |
|---|---|
| `melocreate.jar` | The MIDlet (preverified Java 1.2 class files, about 37 KB) |
| `melocreate.jad` | Application descriptor, with signing fields |
| `melocreate.zip` | A copy of the same classes as the JAR |
| `LICENSE` | MIT |
| `python/` | Desktop recreation in Python/Tkinter (no SMS sending). See [python/README.md](python/README.md). |
| `web/` | Browser recreation in a single `index.html`, which also works on phones (no SMS sending). See [web/README.md](web/README.md). |

### Code structure (from the compiled classes)

```
GUIComposer/
├── MeloCreate              MIDlet entry point; switches between screens
├── UI/
│   ├── Editor              Staff canvas: drawing, key handling, playback timer
│   ├── DurationEdit        Note-value / dot / triplet / style picker
│   ├── Menu                Title · Tempo · Save · Load · Send
│   ├── TextEdit            Title and tempo input boxes
│   ├── HelpDoc             Key-binding help screens
│   ├── Img                 Cuts note, clef and accidental glyphs from allStaff.png
│   ├── Style               Fonts and layout constants
│   └── allStaff.png        Sprite sheet of all musical symbols
├── Data/
│   ├── Ringtone            Singleton tune model (128 notes: duration, dot, pitch, style)
│   ├── NokiaRingtone       Encoder for the Smart Messaging bit-packed ringtone format
│   ├── Recorder            Wrapper around the RMS RecordStore
│   └── HttpService         Minimal HTTP GET client
├── TonePlayer/
│   ├── TonePlayer          Player base class; picks Nokia or dummy at run time
│   └── NokiaTonePlayer     Playback through com.nokia.mid.sound.Sound
└── Networking/
    └── SendUI              Clickatell SMS form and send log
```

## History

Written by Alan Ong (pangchi) around 2002–2003, during the era of Nokia "Composer" ringtones and Smart Messaging. MeloCreate was originally distributed through a WAP page on `home.pacific.net.sg`. The class files in this JAR are dated October 2003.

## License

MIT. See [LICENSE](LICENSE).
