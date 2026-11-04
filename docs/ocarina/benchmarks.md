# TTS benchmarks and findings (2026-11-03, M1 Max 32 GB)

Chatterbox Multilingual, about 25 words of Dutch, Polish and French, run after a warm-up:

| Engine | Dutch | Polish | French | Seconds per second of audio | Load | Peak RAM |
|---|---|---|---|---|---|---|
| MLX (`mlx-audio`, `mlx-community/chatterbox-multilingual-v3`) | 3.3 s | 3.8 s | 3.3 s | **0.54** | 2.5 s | 3.5 GB |
| PyTorch MPS | 27.7 s | 30.3 s | 27.0 s | 4.2 | 11.5 s | 5.3 GB |
| PyTorch CPU | 33.2 s | 37.5 s | 33.0 s | 5.3 | 11.7 s | 7.2 GB |

- MLX is the default engine (faster than real time). PyTorch is only ~20% faster on GPU than CPU.
- The MLX model has no built-in voice: it needs a reference clip (`ref_audio`). Ours is
  `ocarina/tts/voices/dutch.wav` (a Dutch sample, with its transcript in `dutch.txt`).
- All three languages sound fine; the voice is too fast for a learner, so playback speed (0.5x to
  1.0x, pitch kept) is a reader control. Speaking pace is not
  controllable in the model (2026-11-03, Dutch sentence, 3.8 s at default): `speed` is ignored by
  Chatterbox, `cfg_weight` 0.0 gives +8%, and a reference clip slowed to 0.8x gives only +4%.
  So a "slow voice" can only come from stretching the audio, which the player already does live.
- Second engine, chosen 2026-11-03: **Audio8 TTS Realistic 0.6B** (mlx-audio, Apache-2.0, 2.6 GB,
  nl/pl/fr among 23 languages, 44.1 kHz). CosyVoice2 was dropped: it is not in mlx-audio and does not cover
  nl/pl/fr. On the M1 Max it voices a 23-sentence Dutch book in 46 s (about 0.7 s per second of audio; single
  sentences 0.8 to 1.1) and loads in 0.2 s. It speaks about 40% slower than Chatterbox by itself (the same Dutch
  sentence is 5.3 s against 3.8 s), which suits a learner. It speaks in its own voice; it only imitates a clip when
  given the exact words spoken in it. Quality of the voices was not judged by ear: listen and compare.
- Not benchmarked: Parkiet (Dutch only), Voxtral (nl, fr, not pl), KugelAudio (7B, 24 languages).
- A whole 3-page, 77-sentence Polish book voices in about two minutes.
- Licenses: `mlx-audio` MIT; model MIT. Check each model's license before adding it to the catalog.
- Raw scripts and results from this round live outside the repo in `~/Lute-Ocarina/bench`.

## Local language model for translation (2026-11-03, M1 Max)

- **Qwen3-4B-Instruct-2507, 4-bit (mlx-lm, Apache-2.0, 2.3 GB):** loads in 0.6 s, translates a sentence in 0.2 to 0.4 s
  (about 45 tokens/s), about 2.5 GB of memory while loaded. Good for ordinary sentences in Polish, Dutch and French.
  It invents words for rare vocabulary ("Smoczy Skarb", dragon treasure, became "Silver Coin") and mangles names
  ("Boucle d'or" became "Orloop"). A short prompt works best: adding "stay close to the original wording" made the
  translations stilted.
- **Qwen3-8B (4.6 GB):** about twice as slow, not noticeably more reliable on names or grammar notes.
- **Not shipped, on purpose:** free-form "explain this word and its grammar" (it gave wrong base forms: *szkole* from
  "szkolić", *af* in *zich afvragen*, *entra* as passé composé) and "pick the right dictionary sense" (it chose
  "to ice (cover with icing)" for *une glace*). Wrong grammar notes would mislead a learner; definitions come from Wiktionary.
- Setup for the packaged app: `pip install mlx-lm` in `.venv` and `.venv-build`; `mlx_lm` is in `desktop/setup.py`.

## Higgs TTS 3-4b (added by the user, 2026-11-04, M1 Max)

- `bosonai/higgs-tts-3-4b`: the original PyTorch release, 9.3 GB bf16 (license "other"), model type
  `higgs_multimodal_qwen3`, which mlx-audio handles with its `higgs_audio_v3` code. Speaks Polish.
- It first failed with "No module named 'torch'": the audio codec lives in the same bfloat16 checkpoint, mlx-audio reads
  it with safetensors' MLX reader (which goes through numpy, and numpy has no bfloat16; true for safetensors 0.8.0, the
  newest), and falls back to PyTorch. `ocarina/tts/mlx_compat.py` makes the worker read those tensors with `mx.load`
  instead, so PyTorch is not needed.
- Speed: loads in about 5 s once cached; 0.85 s of compute per second of audio (Chatterbox is 0.54). A 55 s Polish book took
  57 s. Quality by ear: not judged by me.
