# TTS benchmarks and findings (2026-11-03, M1 Max 32 GB)

Chatterbox Multilingual, about 25 words of Dutch, Polish and French, run after a warm-up:

| Engine | Dutch | Polish | French | Seconds per second of audio | Load | Peak RAM |
|---|---|---|---|---|---|---|
| MLX (`mlx-audio`, `mlx-community/chatterbox-multilingual-v3`) | 3.3 s | 3.8 s | 3.3 s | **0.54** | 2.5 s | 3.5 GB |
| PyTorch MPS | 27.7 s | 30.3 s | 27.0 s | 4.2 | 11.5 s | 5.3 GB |
| PyTorch CPU | 33.2 s | 37.5 s | 33.0 s | 5.3 | 11.7 s | 7.2 GB |

- MLX is the default engine (faster than real time). PyTorch is only ~20% faster on GPU than CPU.
- The MLX model has no built-in voice: it needs a reference clip (`ref_audio`). Ours is
  `ocarina/tts/voices/default.wav` (a clip from the PyTorch run).
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
