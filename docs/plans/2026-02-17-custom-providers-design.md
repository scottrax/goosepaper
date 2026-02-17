# Custom Goosepaper Providers Design

## Goal

Extend goosepaper with custom story providers for XKCD comics, NASA APOD, word search puzzles, and crossword puzzles. Beef up RSS feeds and subreddits. Target: readable on both reMarkable e-ink and screens.

## Architecture

Custom Python provider files are placed in `providers/` in the project directory. A patched `util.py` is also placed there. The `GenerateNews.command` script mounts the project directory and copies providers into the container at runtime before invoking goosepaper.

### Custom Providers

1. **XKCDStoryProvider** - Fetches latest comic from `xkcd.com/info.0.json`, renders `<img>` with alt text caption
2. **NasaApodStoryProvider** - Fetches from NASA APOD API (no key, demo key), renders photo + explanation
3. **WordSearchStoryProvider** - Generates a random word search grid as an HTML table with word bank
4. **CrosswordStoryProvider** - Generates a simple crossword from a word/clue list as an HTML table with clues

### Provider Interface

Each provider extends `StoryProvider` and implements `get_stories()` returning `List[Story]`. Stories use `body_html` for rich content (images, HTML tables).

### Integration

A patched `util.py` adds the new providers to `StoryProviderConfigNames`. The launch script copies the patched files into the container's Python path before running goosepaper.

### Config additions

- More RSS feeds: AP News, tech news
- More subreddits: r/todayilearned, r/science, r/pics
- New providers: xkcd, nasa_apod, word_search, crossword

## Puzzle Design

- **Word search**: 15x15 grid, ~10 themed words, monospace HTML table, word bank below
- **Crossword**: Simple grid from ~10-15 word/clue pairs, numbered cells, across/down clue lists

Both render as HTML tables with inline CSS for clean grid display on e-ink and screen.
