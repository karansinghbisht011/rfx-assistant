"""Catalogue loading and candidate search. The CSV is the golden record (section 7)."""

import re
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

from app import config
from app.schemas.rfq import CatalogueCandidate

REQUIRED_COLUMNS = ["commodity_code", "commodity_title", "class_title", "default_unit"]


class CatalogueError(RuntimeError):
    pass


def normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse spaces."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def _singular(text: str) -> str:
    """Crude plural folding used only to decide whether two names are the same."""
    return " ".join(w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in text.split())


class Catalogue:
    def __init__(self, frame: pd.DataFrame):
        missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
        if missing:
            raise CatalogueError(f"Catalogue is missing columns: {', '.join(missing)}")
        if frame["commodity_code"].duplicated().any():
            raise CatalogueError("Catalogue has duplicate commodity codes")
        bad_units = set(frame["default_unit"]) - set(config.CANONICAL_UNITS)
        if bad_units:
            raise CatalogueError(f"Catalogue has non-canonical units: {sorted(bad_units)}")
        self._frame = frame.reset_index(drop=True)
        self._norm_titles = [normalize(t) for t in self._frame["commodity_title"]]
        self._folded_titles = [_singular(t) for t in self._norm_titles]
        self._by_code = {code: i for i, code in enumerate(self._frame["commodity_code"])}

    @classmethod
    def load(cls, path: Path = config.CATALOGUE_PATH) -> "Catalogue":
        try:
            frame = pd.read_csv(path, dtype=str).fillna("")
        except (OSError, pd.errors.ParserError) as exc:
            raise CatalogueError(f"Could not read the catalogue: {exc}") from exc
        return cls(frame)

    def __len__(self) -> int:
        return len(self._frame)

    def _candidate(self, index: int, score: float) -> CatalogueCandidate:
        row = self._frame.iloc[index]
        return CatalogueCandidate(
            code=row["commodity_code"],
            title=row["commodity_title"],
            class_title=row["class_title"],
            default_unit=row["default_unit"] or "Nos",
            score=round(float(score), 1),
        )

    def by_code(self, code: str) -> CatalogueCandidate | None:
        index = self._by_code.get(code)
        return None if index is None else self._candidate(index, 100)

    def exact(self, term: str) -> CatalogueCandidate | None:
        """A single entry whose title equals the term, ignoring case, punctuation and plurals."""
        folded = _singular(normalize(term))
        hits = [i for i, t in enumerate(self._folded_titles) if t == folded]
        return self._candidate(hits[0], 100) if len(hits) == 1 else None

    def shortlist(self, terms: list[str], limit: int = config.SHORTLIST_SIZE) -> list[CatalogueCandidate]:
        """Best candidates across all search terms, highest score first."""
        best: dict[int, float] = {}
        for term in terms:
            query = normalize(term)
            if not query:
                continue
            for _, score, index in process.extract(query, self._norm_titles, scorer=fuzz.WRatio, limit=limit):
                best[index] = max(best.get(index, 0.0), score)
        ranked = sorted(best.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        return [self._candidate(i, s) for i, s in ranked]

    def decide(self, terms: list[str], candidates: list[CatalogueCandidate]) -> tuple[str, CatalogueCandidate | None]:
        """Return (status, winner). Code resolves clear matches; everything else goes to G2 or the buyer."""
        for term in terms:
            hit = self.exact(term)
            if hit:
                return "exact", hit
        if not candidates or candidates[0].score < config.MATCH_LOW:
            return "unmatched", None
        top = candidates[0]
        runner_up = candidates[1].score if len(candidates) > 1 else 0.0
        if top.score >= config.MATCH_HIGH and top.score - runner_up >= config.MATCH_MARGIN:
            return "fuzzy", top
        return "ambiguous", None
