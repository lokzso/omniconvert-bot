# OmniConvert MAX
Telegram universal file converter.

## Features
- Images incl. HEIC/HEIF: JPG/PNG/WEBP/BMP/TIFF/PDF
- Video: MP4/MKV/WEBM/MOV/GIF + audio extraction
- Audio: MP3/WAV/FLAC/M4A/OGG/OPUS
- Office/docs via headless LibreOffice
- PDF -> JPG/PNG/TXT
- ZIP/7Z/TAR/TAR.GZ repacking
- Quality, resolution and bitrate controls
- Compression presets
- Batch conversion -> ZIP
- Merge PDF and images -> one PDF
- Automatic file type detection

## Run with Docker
1. Copy `.env.example` to `.env` and put your BotFather token in `BOT_TOKEN`.
2. `docker build -t omniconvert .`
3. `docker run --env-file .env --rm omniconvert`

## Run without Docker (Linux)
Install ffmpeg, LibreOffice, poppler-utils, p7zip-full, then `pip install -r requirements.txt` and `python bot.py`.

Telegram/cloud upload limits still apply. Conversion only exists where the source and target formats have a meaningful mapping.
