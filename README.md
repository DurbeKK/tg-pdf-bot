[![GitHub](https://img.shields.io/github/license/DurbeKK/tg_pdf_bot)](https://github.com/DurbeKK/tg_pdf_bot/blob/main/LICENSE) [![Telegram](https://img.shields.io/badge/telegram-%40vivyTgBot-blue)](https://t.me/vivyTgBot)

# Telegram PDF Bot
## _Working with PDFs is now a bit easier!_

This bot aims to help people by making their work PDFs a bit easier. This is a work in progress and hopefully in the future I won't be embarassed to show this code to people. But in case you somehow did stumble upon this, please don't judge this too hard.

## Features

- Merging: Merge multiple PDF files into one PDF file
- Compression: Compress a PDF file (can only compress one file at a time)
- Encryption/Decryption: this is all done with the PDF standard encryption handler
- Splitting: Split PDF (extract certain pages from your PDF, saving those pages into a separate file)
- Conversion: Convert Word Documents/Images to PDF

## Installation

Change the variables in the .env.example file and then rename the file to .env.
Then I'd highly recommend that you just build the docker image from Dockerfile, but if you want to do it manually, then run the following in your terminal:
```sh
apt-get update && apt-get install -y ghostscript libreoffice
```

Create and activate a virtual environment and then install the necessary python packages
```sh
pip install -r requirements.txt
```

Run the bot with
```sh
python app.py
```

