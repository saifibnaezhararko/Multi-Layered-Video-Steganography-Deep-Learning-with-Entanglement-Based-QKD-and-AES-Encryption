# StegaWe91 – Project Description

## Project ta ki?

Eta ekta **capstone project** (QKD + QML, Mahdy Sir er under e). Idea: ekta **secret image** ke arekta **cover image** er bhitore **lukiye dewa (steganography)**, tarpor oi image ke **quantum key diye AES encrypt** kora. Shob kichu ekta **PyQt5 desktop app** e use kora jay.

**Pura flow:**
1. Cover + Secret image → Deep Learning model → ekta **steg image** (dekhte cover er moto, kintu bhitore secret lukano)
2. Steg image → **AES encryption** (key ashe quantum protocol theke)
3. Decrypt → Reveal → secret image abar ber kora

---

## Folder structure

```
stegaWe91/
├── README.md            → shudhu project name ar GitHub link
├── requirements.txt     → tensorflow, keras, PyQt5, qiskit, pycryptodome, pillow etc.
├── images/              → output image gulo (steg_image.png, secret_out.png, steg_image.dec.png)
└── app/
    ├── ui/                      → GUI (PyQt5)
    ├── models/
    │   ├── DEEP_STEGO/          → image hide/reveal er neural network
    │   └── encryption/aes.py    → quantum key + AES
    ├── main_CLI_v1.py           → purano command-line version
    └── steg_image.png           → hide korar por output
```

---

## 1. `app/models/encryption/aes.py` – Quantum key + AES

- **Qiskit** diye **E91 QKD protocol** simulate kore (Ekert-91, entangled qubit pair based).
- 500 ta singlet (entangled pair) toiri hoy. Alice ar Bob randomly 3 ta measurement basis theke ekta kore choose kore.
- Jei jei jaygay basis match kore (A2–B1 ba A3–B2), oi bit gulo diye **aliceKey** ar **bobKey** toiri hoy (duitai same hoyar kotha, noise na thakle).
- `encrypt(image_path, key)`: image → base64 → key er SHA-256 hash → **AES-256-CBC** (random IV soho) → **original file ta overwrite** kore dey.
- `decrypt(...)`: ulta kaj kore; key bhul hole `"Wrong Key"` dey, thik hole `.dec.png` file banay.
- ⚠️ Module import korlei QKD simulation chole (500 ta circuit), tai app start e ektu shomoy lage. Ar `encrypt` original file overwrite kore.

## 2. `app/models/DEEP_STEGO/` – Deep Steganography

Baluja er "Hiding Images in Plain Sight" paper er moto CNN based approach.

- **`train.py`** – model architecture ar training. 3 ta network:
  - *Prepare network*: secret image process kore (3×3, 4×4, 5×5 conv)
  - *Hiding network*: cover + prepared secret mix kore steg image banay
  - *Reveal network*: steg image theke secret ber kore (+ GaussianNoise)
  - Dui ta custom loss: `hide_conv_f` (cover er moto dekhte) ar `revl_conv_f` (secret thik moto ferot) – weight 1.0 ar 0.75
- **`hide_image.py`** – `hide.h5` load kore, duita image **224×224** e resize kore, normalize kore model e dey, output `images/steg_image.png` e save kore.
- **`reveal_image.py`** – `reveal.h5` diye steg image theke secret ber kore (`secret_out.png`).
- **`models/`** – trained model (`hide.h5`, `reveal.h5`) ar architecture diagram PNG.
- **`checkpoints/`** – training checkpoint (`steg_model-06-0.03.hdf5`).
- **`Utils/`** – helper: `preprocessing.py` (normalize), `customLossWeight.py` (loss), `eval.py`, `enhance.py` (opencv), `test.py`.

## 2b. Video Steganography (video-in-video)

Secret video er frame *i* ke cover video er frame *i* er bhitore lukano hoy, same `hide.h5` / `reveal.h5` model diye (frame-by-frame, batch e).

- **`hide_video.py`** – `hide_video(cover, secret)` → `videos/steg_video.avi`
- **`reveal_video.py`** – `reveal_video(stego)` → `videos/secret_out_video.avi`
- **`Utils/video_io.py`** – OpenCV diye frame read/write (BGR↔RGB, 224×224 resize, lossless writer)

Terminal theke (repo root e):
```
python -m app.models.DEEP_STEGO.hide_video --cover cover.mp4 --secret secret.mp4
python -m app.models.DEEP_STEGO.reveal_video --stego videos/steg_video.avi
```
(`--max-frames 30` dile shudhu prothom 30 frame – quick test er jonno; CPU te frame beshi hole shomoy beshi lage.)

QKD + AES same thake: steg video (`.avi`) ke Encryption page e encrypt kora jay (E91 key → SHA-256 → AES), decrypt korle `steg_video.dec.avi` hoy, tarpor Video Reveal.

⚠️ Note:
- Steg video **lossless** (PNG-in-AVI) – eta mp4 e convert korle ba WhatsApp/YouTube e upload korle hidden video nosto hoye jay.
- Output **224×224**, audio nei, frame shonkhya = duita video er moddhe chhoto tar shoman, fps = cover er fps.
- E91 key protibar app start e notun hoy, tai encrypt ar decrypt same session e korte hobe.

## 2c. Audio Steganography (`app/models/AUDIO_STEGO/`)

Cover hocche ekta **WAV audio**, secret hote pare **je kono file** (text, image, audio clip, steg video) ba ekta **text message**. Ekhane order ulta: age **encrypt**, tarpor **lukano** – tai je file pathano hoy sheta shunte shadharon gaan/audio er motoi, dekhe bojha jay na je bhitore kichu ache.

**Flow:**
1. Secret → **AES-256-GCM** encrypt (key = E91 key er SHA-256, image/video er moto same key)
2. Encrypted data → cover audio er sample gulor **LSB (least significant bit)** e boshano hoy
3. Kon kon sample e bit boshbe sheta **key diye shuffle** kora – tai change gulo pura file e chhoriye thake, key chhara khuje pawa jay na
4. Secret fit korate joto kom LSB lage (1–4) sheta nijei choose kore (`--bits` diye fix kora jay)

- **`audio_lsb.py`** – WAV read/write, bit embed/extract, capacity hishab (8/16/24/32-bit PCM, mono/stereo)
- **`hide_audio.py`** – `hide_audio(cover, secret_file, key, message=...)` → `audio/steg_audio.wav`
- **`reveal_audio.py`** – `reveal_audio(stego, key)` → `audio/revealed/<original file name>`
- **`app/models/encryption/aes_payload.py`** – AES-GCM (bhul key ba file e ekta bit change holeo dhora pore)
- **`app/models/encryption/keyfile.py`** – E91 key file e save/load (CLI te hide ar reveal alada process e chole, tai key file lage)

Terminal theke (repo root e):
```
python -m app.models.AUDIO_STEGO.hide_audio --cover cover.wav --secret secret.png
python -m app.models.AUDIO_STEGO.hide_audio --cover cover.wav --message "5 tay dekha hobe"
python -m app.models.AUDIO_STEGO.reveal_audio --stego audio/steg_audio.wav
```
Prothombar hide korle E91 simulation chole ar key `audio/e91_key.txt` e save hoy; reveal sheta use kore (`--key-file` diye onno file deya jay). **Key file kauke diba na / git e dibe na** (`audio/` gitignored).

⚠️ Note:
- Shudhu **WAV** (uncompressed PCM). MP3/AAC hole age WAV e convert koro (Audacity ba ffmpeg).
- Steg audio ke mp3 e convert korle ba WhatsApp e voice hishebe pathale hidden data nosto hoye jay (reveal e error dibe).
- Capacity: 44.1 kHz stereo 16-bit audio te proti second e ~11 KB (1 LSB) – 30 second e ~322 KB, 4 LSB e ~1.3 MB.
- Quality: 16-bit cover e 1 LSB e SNR ~80–110 dB (shona jay na). 8-bit cover e change beshi (SNR ~55 dB).

## 3. `app/ui/` – GUI (`main.py`)

`MainAppWindow` class, dark theme. Left sidebar e 8 ta button:

| Button | Kaj |
|---|---|
| **Image Hide** | cover + secret select → `hide_image()` → steg image dekhay, download kora jay |
| **Encryption** | image select → `aes.encrypt(file, aes.aliceKey)` |
| **Decryption** | encrypted file → `aes.decrypt(file, aes.bobKey)` |
| **Image Reveal** | steg image → `reveal_image()` → secret ferot |
| **Video Hide** | cover + secret video → `hide_video()` → steg video (background thread, progress bar) |
| **Video Reveal** | steg video → `reveal_video()` → secret video ferot |
| **Audio Hide** | cover WAV + secret file / message → `hide_audio()` (aliceKey diye encrypt) → steg audio |
| **Audio Reveal** | steg WAV → `reveal_audio()` (bobKey) → secret ferot; image hole preview, text hole message dekhay |

- `components/` – custom background widget, text box
- `styles/style.qss` – styling
- `assets/` – dummy placeholder image
- `test/berry/` – onek gulo `_256.jpg` sample image (testing er jonno)
- Note: `main.py` er shuru te TensorFlow age import kora hoyeche, karon Windows e PyQt5 age load korle TF er DLL error dey.

## 4. `app/main_CLI_v1.py`

Purano terminal version. Eta ekhon **bhanga**: `blowfish` ar `ESRGAN` import kore, kintu ei folder e oi module gulo nei (onno project "InvisiCipher" theke neya). GUI-ta-i ashol version.

---

## Chhoto kichu note

- `.idea/`, `__pycache__/` git e ashe gese – `.gitignore` dile bhalo.
- Dataset (`dataset/`) folder repo te nei, tai `train.py` chalate hole alada kore dataset lagbe.
