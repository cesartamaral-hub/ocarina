# Ocarina: credits and licences

Ocarina is a personal language-study app. It is a fork of **Lute v3** and builds on the work below. Thank you to everyone who made it.

## Lute v3

Ocarina is a hard fork of [Lute v3](https://github.com/LuteOrg/lute-v3) (Learning Using Texts), Copyright (c) 2023 Jeff Zohrab, released under the MIT licence (see `LICENSE.txt`, which must stay with every copy). The reader, the parser, terms and statuses, the database and the book import come from Lute.

## Dictionary data

- **Wiktionary**, via **Wiktextract** (Tatu Ylonen, [kaikki.org](https://kaikki.org)) for the downloadable full packs, and via **WikDict** ([wikdict.com](https://www.wikdict.com), Karl Bartel) for the small packs that come with the app (German, Spanish, French, Italian, Dutch, Polish, Portuguese to English). The entries are written by the Wiktionary contributors. Licence: **CC BY-SA 4.0** ([creativecommons.org/licenses/by-sa/4.0](https://creativecommons.org/licenses/by-sa/4.0/)), and Wiktionary's text is also available under the GFDL.
- Changes made by Ocarina: the data is converted into a compact SQLite file, with entries grouped by word and inflected forms linked to their base word. Because of the share-alike term, **these converted packs stay under CC BY-SA 4.0**; the licence of the app's code is not affected.
- Definitions that are fetched online come from the English Wiktionary under the same licence.

## Models (downloaded by the user, never bundled)

| Model | Made by | Licence |
|---|---|---|
| Chatterbox Multilingual v3 (MLX) | Resemble AI; MLX conversion by mlx-community | MIT |
| Audio8 TTS Realistic 0.6B | nativ-community | Apache 2.0 |
| Qwen3 4B and 8B, Qwen3 Forced Aligner | Alibaba Cloud (Qwen team); MLX conversion by mlx-community | Apache 2.0 |
| TranslateGemma 4B and 12B | Google | Gemma Terms of Use |
| Whisper Large v3 Turbo | OpenAI; MLX conversion by mlx-community | MIT |

Gemma is provided under and subject to the Gemma Terms of Use, [ai.google.dev/gemma/terms](https://ai.google.dev/gemma/terms). Models you add yourself keep the licence of their authors; Ocarina shows it when you add one.

## Software

Ocarina runs on: **MLX**, **mlx-lm**, **mlx-audio** (Apple and contributors, MIT); **Hugging Face Hub**, **Transformers**, **Tokenizers** and **safetensors** (Hugging Face, Apache 2.0); **NumPy** and **SciPy** (BSD); **SoundFile** (BSD); **Flask**, **Flask-SQLAlchemy** and **Flask-WTF** (BSD); **SQLAlchemy** (MIT); **Waitress** (ZPL 2.1); **Requests** (Apache 2.0); **Beautiful Soup**, **PyYAML**, **pyparsing**, **toml**, **platformdirs** and **ahocorapy** (MIT); **pypdf** (BSD); **openepub** (Unlicense); **pywebview** (BSD, the window); **py2app** (MIT, the packaging); **trafilatura** (Apache 2.0, reading web pages); **yt-dlp** (Unlicense, YouTube audio and captions); **React** (MIT, the interface). Their licences are in their own packages.

**FFmpeg** (the FFmpeg developers, [ffmpeg.org](https://ffmpeg.org)) converts audio. The copy inside the app is built from the official source with LGPL v2.1 parts only (`scripts/build_ffmpeg.sh`), is a separate program that Ocarina starts, and its licence is `ffmpeg-LICENSE.txt` next to this file. Anyone may replace it: put another `ffmpeg` in `Contents/Resources/bin`.

## Online services (only when Work offline is off, and only when used)

- **MyMemory** (translated.net) and **DeepL**: sentence translation, under their own terms; DeepL needs the user's own key.
- **Wiktionary** and **Wikimedia Commons**: definitions and recordings of single words. Each recording keeps its own licence and author, shown on its Commons page.
- **Google Translate**'s voice: an unofficial address, used only when chosen, under Google's terms.
- **YouTube**: videos are played with YouTube's own player and fetched with yt-dlp, under YouTube's terms. Use your own judgement about what you may download.

## Other

The CEFR vocabulary figures shown on the Vocabulary page are common frequency-based estimates, not an official scale. The app icon is Ocarina's own.
