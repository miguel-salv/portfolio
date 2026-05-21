# miguelsalv.com

Personal website for Miguel Salvacion, hosted on GitHub Pages.

The site is built in [Framer](https://framer.com) and synced here automatically via a Python scraper that strips Framer branding and exports static HTML.

## How it works

`extract.py` crawls the Framer site, cleans the HTML, and writes it to this repo. A [GitHub Action](.github/workflows/sync-framer.yml) runs the script twice daily and commits any changes.

## Manual sync

```bash
pip install requests beautifulsoup4
python extract.py
```
