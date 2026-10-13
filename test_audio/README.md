# Test audio

Open-licensed recordings for testing the audio steganography (`app/models/AUDIO_STEGO/`). They come from the librosa example-data repository (https://github.com/librosa/data). Each file's SHA-256 matches librosa's registry.

| File | What it is | Format | License |
|---|---|---|---|
| `brahms_hungarian_dance_5.ogg` / `.wav` | Brahms, *Hungarian Dance No. 5*, US Army Strings, via Musopen | 45.8 s, 44.1 kHz stereo | Public Domain (PDM 1.0) |
| `tchaikovsky_sugar_plum_fairy_kevin_macleod.ogg` | *P. I. Tchaikovsky: Dance of the Sugar Plum Fairy* by Kevin MacLeod, via Free Music Archive | 119.9 s, 44.1 kHz stereo | CC BY 3.0 |
| `vibe_ace_kevin_macleod.ogg` | *Vibe Ace* by Kevin MacLeod, via Free Music Archive | 61.5 s, 44.1 kHz stereo | CC BY 3.0 |
| `librispeech_5703-47212-0000_speech.ogg` | LibriSpeech (OpenSLR SLR12) utterance 5703-47212-0000, *The Ashiel Mystery*, read by Garth Comira | 14.8 s, 16 kHz mono (speech) | CC BY 4.0 |
| `glacier_bay_humpback_whale.ogg` | Glacier Bay humpback whale song, recorded by NPS / Chris Gabriele, 2020-11-13 | 64.8 s, 44.1 kHz mono | Public domain (US National Park Service) |

## Attribution (required by CC BY)

- "P. I. Tchaikovsky: Dance of the Sugar Plum Fairy" and "Vibe Ace" by Kevin MacLeod (incompetech.com), licensed under CC BY 3.0: https://creativecommons.org/licenses/by/3.0/
- LibriSpeech ASR corpus (V. Panayotov, G. Chen, D. Povey, S. Khudanpur), https://www.openslr.org/12/, licensed under CC BY 4.0: https://creativecommons.org/licenses/by/4.0/

## Using them as covers

The steganography needs **uncompressed PCM WAV** covers. `brahms_hungarian_dance_5.wav` is ready to use. Convert the others with ffmpeg (`-map 0:a` skips the cover art embedded in `vibe_ace`):

```
ffmpeg -i vibe_ace_kevin_macleod.ogg -map 0:a -c:a pcm_s16le vibe_ace_kevin_macleod.wav
```

At 1 LSB per sample, the 44.1 kHz stereo covers hold about 11 KB of secret per second: the Brahms WAV holds about 493 KB, or about 1.9 MB at 4 LSBs.
