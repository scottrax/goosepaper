import random
from typing import List, Tuple, Optional, Dict

from goosepaper.storyprovider.storyprovider import StoryProvider
from goosepaper.story import Story
from goosepaper.util import PlacementPreference

PUZZLE_SETS = [
    {
        "theme": "Geography",
        "words": [
            ("RIVER", "A flowing body of water"),
            ("MOUNTAIN", "A large natural elevation"),
            ("ISLAND", "Land surrounded by water"),
            ("DESERT", "An arid, sandy region"),
            ("CANYON", "A deep gorge in the earth"),
            ("GLACIER", "A slow-moving mass of ice"),
            ("PLATEAU", "A flat elevated landform"),
            ("VOLCANO", "An opening that erupts lava"),
            ("VALLEY", "Low area between hills"),
            ("OCEAN", "A vast body of salt water"),
            ("DELTA", "Sediment deposit at river mouth"),
            ("TUNDRA", "Cold treeless biome"),
        ],
    },
    {
        "theme": "Science",
        "words": [
            ("ATOM", "Smallest unit of an element"),
            ("CELL", "Basic unit of life"),
            ("GRAVITY", "Force that pulls objects together"),
            ("PHOTON", "A particle of light"),
            ("ENZYME", "A biological catalyst"),
            ("QUARK", "Subatomic particle in protons"),
            ("PLASMA", "Fourth state of matter"),
            ("NEURON", "A nerve cell"),
            ("PRISM", "Splits white light into colors"),
            ("ORBIT", "Path around a celestial body"),
            ("GENE", "Unit of heredity"),
            ("LENS", "Focuses light rays"),
        ],
    },
    {
        "theme": "Literature",
        "words": [
            ("NOVEL", "A long fictional narrative"),
            ("PROSE", "Ordinary written language"),
            ("FABLE", "A short moral story"),
            ("VERSE", "A line of poetry"),
            ("GENRE", "A category of literature"),
            ("PLOT", "Sequence of story events"),
            ("THEME", "Central idea of a work"),
            ("STANZA", "A grouped set of poem lines"),
            ("IRONY", "Opposite of what is expected"),
            ("SATIRE", "Using humor to criticize"),
            ("EPIC", "A long heroic narrative poem"),
            ("MYTH", "A traditional symbolic story"),
        ],
    },
    {
        "theme": "Nature",
        "words": [
            ("FOREST", "A dense area of trees"),
            ("CORAL", "Marine organism forming reefs"),
            ("POLLEN", "Powder from flowering plants"),
            ("FALCON", "A fast bird of prey"),
            ("MAPLE", "Tree with lobed leaves"),
            ("LICHEN", "Fungus-algae symbiosis"),
            ("MOSS", "Small green flowerless plant"),
            ("HERON", "A long-legged wading bird"),
            ("FERN", "A feathery leafed plant"),
            ("BIRCH", "A white-barked tree"),
            ("ACORN", "Seed of an oak tree"),
            ("BROOK", "A small stream"),
        ],
    },
]


class CrosswordStoryProvider(StoryProvider):
    def __init__(self, num_words: int = 10, grid_size: int = 15):
        self.num_words = num_words
        self.grid_size = grid_size

    def _try_place(
        self,
        grid: List[List[str]],
        word: str,
        r: int,
        c: int,
        dr: int,
        dc: int,
    ) -> bool:
        size = self.grid_size
        end_r = r + dr * (len(word) - 1)
        end_c = c + dc * (len(word) - 1)
        if not (0 <= end_r < size and 0 <= end_c < size):
            return False

        # Check placement validity - must not create invalid adjacencies
        for i, ch in enumerate(word):
            nr, nc = r + dr * i, c + dc * i
            existing = grid[nr][nc]
            if existing != "" and existing != ch:
                return False
            # If cell is empty, check that we don't run parallel to another word
            if existing == "":
                # Check perpendicular neighbors (not along our direction)
                for pr, pc in [(-dc, -dr), (dc, dr)] if (dr, dc) != (0, 0) else []:
                    adj_r, adj_c = nr + pr, nc + pc
                    if 0 <= adj_r < size and 0 <= adj_c < size:
                        if grid[adj_r][adj_c] != "":
                            # Only allow if this is an intersection point
                            pass

        # Check cell before start and after end are empty (word boundaries)
        before_r, before_c = r - dr, c - dc
        if 0 <= before_r < size and 0 <= before_c < size and grid[before_r][before_c] != "":
            return False
        after_r, after_c = r + dr * len(word), c + dc * len(word)
        if 0 <= after_r < size and 0 <= after_c < size and grid[after_r][after_c] != "":
            return False

        return True

    def _place_word(
        self,
        grid: List[List[str]],
        word: str,
        r: int,
        c: int,
        dr: int,
        dc: int,
    ):
        for i, ch in enumerate(word):
            nr, nc = r + dr * i, c + dc * i
            grid[nr][nc] = ch

    def _generate(self) -> Tuple[List[List[str]], str, List[Tuple[str, str, int, int, str]]]:
        puzzle_set = random.choice(PUZZLE_SETS)
        theme = puzzle_set["theme"]
        word_clues = list(puzzle_set["words"])
        random.shuffle(word_clues)
        word_clues = word_clues[: self.num_words]
        # Sort by length descending for better placement
        word_clues.sort(key=lambda x: len(x[0]), reverse=True)

        grid = [["" for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        placed = []  # (word, clue, row, col, direction)

        # Place first word in center horizontally
        first_word, first_clue = word_clues[0]
        start_c = (self.grid_size - len(first_word)) // 2
        start_r = self.grid_size // 2
        self._place_word(grid, first_word, start_r, start_c, 0, 1)
        placed.append((first_word, first_clue, start_r, start_c, "across"))

        # Try to place remaining words by finding intersections
        for word, clue in word_clues[1:]:
            best = None
            for pi, (pw, _, pr, pc, pd) in enumerate(placed):
                pdr, pdc = (0, 1) if pd == "across" else (1, 0)
                # Try crossing direction
                new_dr, new_dc = (1, 0) if pd == "across" else (0, 1)
                new_dir = "down" if pd == "across" else "across"

                for i, ch_placed in enumerate(pw):
                    pr_i = pr + pdr * i
                    pc_i = pc + pdc * i
                    for j, ch_new in enumerate(word):
                        if ch_placed == ch_new:
                            # word[j] would land at (pr_i, pc_i)
                            wr = pr_i - new_dr * j
                            wc = pc_i - new_dc * j
                            if self._try_place(grid, word, wr, wc, new_dr, new_dc):
                                best = (word, clue, wr, wc, new_dir, new_dr, new_dc)
                                break
                    if best:
                        break
                if best:
                    break

            if best:
                word, clue, wr, wc, new_dir, new_dr, new_dc = best
                self._place_word(grid, word, wr, wc, new_dr, new_dc)
                placed.append((word, clue, wr, wc, new_dir))

        return grid, theme, placed

    def _to_html(
        self,
        grid: List[List[str]],
        theme: str,
        placed: List[Tuple[str, str, int, int, str]],
    ) -> str:
        size = self.grid_size

        # Assign numbers to starting cells
        number_map: Dict[Tuple[int, int], int] = {}
        num = 1
        # Sort placed words by position (top-to-bottom, left-to-right)
        placed_sorted = sorted(placed, key=lambda x: (x[2], x[3]))
        for word, clue, r, c, direction in placed_sorted:
            if (r, c) not in number_map:
                number_map[(r, c)] = num
                num += 1

        # Find which cells are used
        used = set()
        for word, clue, r, c, direction in placed:
            dr, dc = (0, 1) if direction == "across" else (1, 0)
            for i in range(len(word)):
                used.add((r + dr * i, c + dc * i))

        # Build grid HTML
        black_style = "background: black; width: 1.6em; height: 1.6em; border: 1px solid black;"
        cell_style = (
            "width: 1.6em; height: 1.6em; border: 1px solid black; "
            "text-align: center; vertical-align: middle; position: relative; "
            "font-family: monospace; font-size: 12pt;"
        )

        rows_html = ""
        for r in range(size):
            # Skip rows that are entirely black
            if not any((r, c) in used for c in range(size)):
                continue
            cells = ""
            for c in range(size):
                if (r, c) not in used:
                    cells += f'<td style="{black_style}"></td>'
                else:
                    num_str = ""
                    if (r, c) in number_map:
                        num_str = f'<span style="position: absolute; top: 0; left: 1px; font-size: 7pt;">{number_map[(r, c)]}</span>'
                    cells += f'<td style="{cell_style}; position: relative;">{num_str}</td>'
            rows_html += f"<tr>{cells}</tr>"

        # Build clue lists
        across_clues = []
        down_clues = []
        for word, clue, r, c, direction in placed_sorted:
            n = number_map[(r, c)]
            entry = f"<li><strong>{n}.</strong> {clue} ({len(word)} letters)</li>"
            if direction == "across":
                across_clues.append(entry)
            else:
                down_clues.append(entry)

        across_html = "".join(across_clues) if across_clues else "<li><em>None</em></li>"
        down_html = "".join(down_clues) if down_clues else "<li><em>None</em></li>"
        clues_html = f"""
        <table style="width: 100%; margin-top: 1em; border-collapse: collapse; table-layout: fixed; font-size: 10pt;">
            <tr>
                <td style="width: 50%; vertical-align: top; padding-right: 0.6em;">
                    <h3 style="margin: 0 0 0.25em 0;">Across</h3>
                    <ul style="list-style: none; margin: 0; padding-left: 0;">{across_html}</ul>
                </td>
                <td style="width: 50%; vertical-align: top; padding-left: 0.6em;">
                    <h3 style="margin: 0 0 0.25em 0;">Down</h3>
                    <ul style="list-style: none; margin: 0; padding-left: 0;">{down_html}</ul>
                </td>
            </tr>
        </table>
        """

        return f"""
        <div>
            <table style="border-collapse: collapse; margin: 0 auto;">
                {rows_html}
            </table>
            {clues_html}
        </div>
        """

    def get_stories(self, limit: int = 1, **kwargs) -> List[Story]:
        grid, theme, placed = self._generate()
        body_html = self._to_html(grid, theme, placed)
        return [
            Story(
                headline=f"Crossword: {theme}",
                body_html=body_html,
            )
        ]
