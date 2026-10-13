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

## 3. `app/ui/` – GUI (`main.py`, 676 line)

`MainAppWindow` class, dark theme. Left sidebar e 4 ta button:

| Button | Kaj |
|---|---|
| **Image Hide** | cover + secret select → `hide_image()` → steg image dekhay, download kora jay |
| **Encryption** | image select → `aes.encrypt(file, aes.aliceKey)` |
| **Decryption** | encrypted file → `aes.decrypt(file, aes.bobKey)` |
| **Image Reveal** | steg image → `reveal_image()` → secret ferot |

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
