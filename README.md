<p align="center"><img src="https://raw.githubusercontent.com/j6k4m8/goosepaper/master/docs/goose.svg" width="600" alt="Goosepaper logo"></p>
<h3 align="center">Custom Goosepaper fork for reMarkable daily news + games</h3>

This fork extends upstream Goosepaper with custom providers, styles, layout patches, and a one-click launcher that produces dated PDFs.

## What is different in this fork

- Runtime patching for provider registration and layout behavior:
  - `providers/util_patch.py`
  - `providers/goosepaper_patch.py`
- Custom providers:
  - `forecast` (5-day weather summary)
  - `clean_rss` (RSS extraction with aggressive junk/video cleanup)
  - `reddit_full` (full Reddit post content/images, print-friendly trimming)
  - `xkcd`
  - `nasa_apod`
  - `word_search`
  - `crossword`
- Custom styles:
  - `Vintage`
  - `Broadsheet`
  - `SciFi`
  - `Noir`
- Launcher script `GenerateNews.command` outputs a dated filename:
  - `DailyNews-YYYY-MM-DD.pdf`

## Quick start (recommended)

1. Edit `config.json`.
2. Make the launcher executable once:

```bash
chmod +x GenerateNews.command
```

3. Run it:

```bash
./GenerateNews.command
```

The script mounts the current folder into the Docker container, copies custom providers/styles into runtime paths, applies patches, and generates `DailyNews-YYYY-MM-DD.pdf`.

## Direct Docker run (manual)

If you do not want to use the launcher:

```bash
docker run --rm --platform linux/amd64 \
  -v "$(pwd)":/goosepaper/mount \
  j6k4m8/goosepaper \
  bash -c '
    cp -r /goosepaper/mount/providers /goosepaper/providers
    cp /goosepaper/mount/providers/util_patch.py /goosepaper/goosepaper/util.py
    cp /goosepaper/mount/providers/goosepaper_patch.py /goosepaper/goosepaper/goosepaper.py
    cp -r /goosepaper/mount/styles/* /goosepaper/styles/
    goosepaper -c mount/config.json -o mount/DailyNews-$(date +%Y-%m-%d).pdf
  '
```

## Provider keys in `config.json`

- `forecast`: compact 5-day weather line.
- `clean_rss`: RSS article extraction with cleanup and source naming.
- `reddit_full`: Reddit titles + body/image + stats.
- `nasa_apod`: NASA Astronomy Picture of the Day.
- `xkcd`: latest XKCD comic.
- `word_search`: generated puzzle grid.
- `crossword`: generated crossword + clues.

## Layout behavior

- TOC links are added in the header and point to provider sections.
- Game providers are rendered at the end of the document on dedicated last pages.
- Reddit stories are wrapped to avoid page splits where possible.

## Styles

Set `"style"` in `config.json` to one of:

- `Vintage`
- `Broadsheet`
- `SciFi`
- `Noir`
- Any upstream style still present in `styles/`

## Troubleshooting

- `ValueError: Honk Honk! Syntax Error in config file ...`
  - Validate JSON syntax (missing commas are the most common issue).
- NASA APOD `429 Too Many Requests`
  - `DEMO_KEY` is rate-limited; use your own NASA API key in `providers/nasa_apod.py` if needed.
- Old output name expectations
  - This fork now writes `DailyNews-YYYY-MM-DD.pdf` by default.

## Upstream project

This repo is a fork of upstream Goosepaper:
https://github.com/j6k4m8/goosepaper

See `CONTRIBUTING.md` for general extension patterns.
