import random
from typing import List, Tuple, Optional

from goosepaper.storyprovider.storyprovider import StoryProvider
from goosepaper.story import Story
from goosepaper.util import PlacementPreference

WORD_LISTS = {
    "animals": [
        ("ELEPHANT", "GIRAFFE", "PENGUIN", "DOLPHIN", "TIGER",
         "OCTOPUS", "FALCON", "TURTLE", "JAGUAR", "COBRA"),
    ],
    "space": [
        ("GALAXY", "NEBULA", "PLANET", "COMET", "ORBIT",
         "QUASAR", "PULSAR", "METEOR", "SATURN", "VENUS"),
    ],
    "food": [
        ("BANANA", "MANGO", "PIZZA", "SUSHI", "BREAD",
         "CHEESE", "SALMON", "GARLIC", "PEPPER", "WAFFLE"),
    ],
    "weather": [
        ("THUNDER", "BREEZE", "STORM", "FROST", "CLOUD",
         "TORNADO", "HAIL", "FOGGY", "SLEET", "DRIZZLE"),
    ],
    "ocean": [
        ("CORAL", "WHALE", "SHARK", "TIDE", "REEF",
         "ANCHOR", "TRENCH", "KELP", "HARBOR", "LAGOON"),
    ],
    "music": [
        ("GUITAR", "PIANO", "DRUMS", "VIOLIN", "FLUTE",
         "TEMPO", "CHORD", "MELODY", "RHYTHM", "BASS"),
    ],
}

DIRECTIONS = [
    (0, 1),   # right
    (1, 0),   # down
    (0, -1),  # left
    (-1, 0),  # up
    (1, 1),   # diagonal down-right
    (-1, -1), # diagonal up-left
    (1, -1),  # diagonal down-left
    (-1, 1),  # diagonal up-right
]


class WordSearchStoryProvider(StoryProvider):
    def __init__(self, grid_size: int = 15, num_words: int = 10):
        self.grid_size = grid_size
        self.num_words = num_words

    def _place_word(
        self, grid: List[List[str]], word: str
    ) -> bool:
        size = self.grid_size
        random.shuffle(DIRECTIONS)
        attempts = 0
        for dr, dc in DIRECTIONS:
            for _ in range(50):
                attempts += 1
                r = random.randint(0, size - 1)
                c = random.randint(0, size - 1)
                # Check if word fits
                end_r = r + dr * (len(word) - 1)
                end_c = c + dc * (len(word) - 1)
                if not (0 <= end_r < size and 0 <= end_c < size):
                    continue
                # Check for conflicts
                ok = True
                for i, ch in enumerate(word):
                    nr, nc = r + dr * i, c + dc * i
                    if grid[nr][nc] != "" and grid[nr][nc] != ch:
                        ok = False
                        break
                if ok:
                    for i, ch in enumerate(word):
                        nr, nc = r + dr * i, c + dc * i
                        grid[nr][nc] = ch
                    return True
        return False

    def _generate(self) -> Tuple[List[List[str]], str, List[str]]:
        theme = random.choice(list(WORD_LISTS.keys()))
        words = list(random.choice(WORD_LISTS[theme]))
        random.shuffle(words)
        words = words[: self.num_words]

        grid = [["" for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        placed = []
        for word in words:
            if self._place_word(grid, word):
                placed.append(word)

        # Fill empty cells with random letters
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                if grid[r][c] == "":
                    grid[r][c] = chr(random.randint(65, 90))

        return grid, theme, placed

    def _grid_to_html(self, grid: List[List[str]], theme: str, words: List[str]) -> str:
        cell_style = (
            "width: 6.66%; height: 2.1em; text-align: center; "
            "font-family: monospace; font-size: 14pt; font-weight: bold; "
            "border: 1px solid #666; padding: 0;"
        )
        rows_html = ""
        for row in grid:
            cells = "".join(
                f'<td style="{cell_style}">{ch}</td>' for ch in row
            )
            rows_html += f"<tr>{cells}</tr>"

        word_bank = " &bull; ".join(sorted(words))

        return f"""
        <div style="min-height: 720pt; display: flex; flex-direction: column; justify-content: space-between;">
            <table style="width: 100%; border-collapse: collapse; margin: 0 auto; table-layout: fixed;">
                {rows_html}
            </table>
            <p style="text-align: center; margin: 1em 0 0 0; font-size: 13pt;">
                <strong>Find these words:</strong> {word_bank}
            </p>
        </div>
        """

    def get_stories(self, limit: int = 1, **kwargs) -> List[Story]:
        grid, theme, words = self._generate()
        body_html = self._grid_to_html(grid, theme, words)
        return [
            Story(
                headline=f"Word Search: {theme.title()}",
                body_html=body_html,
            )
        ]
