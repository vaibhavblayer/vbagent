"""Thread-safe lexical blueprint novelty checks for generated problems."""

from __future__ import annotations

import hashlib
import re
import threading
from dataclasses import dataclass
from difflib import SequenceMatcher


def _blueprint_tokens(latex: str) -> list[str]:
    content = re.sub(
        r"\\begin\{(?:solution|idea|hint|finalanswer)\}.*?\\end\{(?:solution|idea|hint|finalanswer)\}",
        " ",
        latex,
        flags=re.DOTALL | re.IGNORECASE,
    )
    content = re.sub(r"(?m)^\s*%.*$", " ", content)
    content = re.sub(r"\d+(?:\.\d+)?", " # ", content)
    content = re.sub(r"\\[A-Za-z]+", " ", content)
    return re.findall(r"[a-z]+|#", content.casefold())


def _shingles(latex: str, width: int = 3) -> set[bytes]:
    """Return compact, stable fingerprints for lexical shingles."""
    tokens = _blueprint_tokens(latex)
    if len(tokens) < width:
        windows = [tokens] if tokens else []
    else:
        windows = [tokens[index:index + width] for index in range(len(tokens) - width + 1)]
    return {
        hashlib.blake2b("\x1f".join(window).encode(), digest_size=16).digest()
        for window in windows
    }


def _artifact_fingerprint(latex: str) -> bytes:
    """Fingerprint rendered source while retaining meaningful numeric changes."""
    content = re.sub(r"(?m)^\s*%.*$", " ", latex)
    content = re.sub(r"\s+", " ", content).strip().casefold()
    return hashlib.blake2b(content.encode(), digest_size=32).digest()


def blueprint_similarity(first: str, second: str) -> float:
    first_shingles = _shingles(first)
    second_shingles = _shingles(second)
    if not first_shingles and not second_shingles:
        return 1.0
    union = first_shingles | second_shingles
    return len(first_shingles & second_shingles) / len(union) if union else 0.0


def variant_stem_similarity(first: str, second: str) -> float:
    """Compare number-normalized question stems while ignoring option churn."""
    first_stem = re.split(r"\\begin\{tasks\}", first, maxsplit=1)[0]
    second_stem = re.split(r"\\begin\{tasks\}", second, maxsplit=1)[0]
    unit_format = re.compile(
        r"\\(?:mathrm|text)\{([^{}]*)\}(?:\s*\^\{?[-+]?\d+\}?)?"
    )

    def normalize_formatting(stem: str) -> str:
        return unit_format.sub(
            lambda match: re.sub(r"[^A-Za-z]+", "", match.group(1)),
            stem,
        )

    first_stem = normalize_formatting(first_stem)
    second_stem = normalize_formatting(second_stem)
    first_tokens = _blueprint_tokens(first_stem)
    second_tokens = _blueprint_tokens(second_stem)
    if not first_tokens and not second_tokens:
        return 1.0
    return SequenceMatcher(
        None,
        first_tokens,
        second_tokens,
        autojunk=False,
    ).ratio()


@dataclass(frozen=True)
class NoveltyResult:
    passed: bool
    max_similarity: float
    closest_id: str | None
    mode: str = "blueprint"


class NoveltyIndex:
    """Accepted-only exact Jaccard index safe for concurrent batch workers.

    An inverted shingle index limits each check to documents that share at least
    one blueprint shingle. Documents with no shared shingle have similarity
    zero, so this produces the same result as an all-pairs scan without its
    quadratic comparison cost.
    """

    def __init__(self):
        self._documents: dict[str, set[bytes]] = {}
        self._postings: dict[bytes, set[str]] = {}
        self._empty_documents: set[str] = set()
        self._artifact_fingerprints: dict[str, bytes] = {}
        self._artifact_postings: dict[bytes, set[str]] = {}
        self._lock = threading.RLock()

    def check(
        self,
        candidate: str,
        threshold: float,
        *,
        exclude_ids: set[str] | frozenset[str] = frozenset(),
    ) -> NoveltyResult:
        with self._lock:
            candidate_shingles = _shingles(candidate)
            if not candidate_shingles:
                closest_id = next(
                    (problem_id for problem_id in self._empty_documents if problem_id not in exclude_ids),
                    None,
                )
                max_similarity = 1.0 if closest_id else 0.0
                return NoveltyResult(
                    passed=max_similarity < threshold,
                    max_similarity=max_similarity,
                    closest_id=closest_id,
                )

            intersections: dict[str, int] = {}
            for shingle in candidate_shingles:
                for problem_id in self._postings.get(shingle, ()):
                    if problem_id in exclude_ids:
                        continue
                    intersections[problem_id] = intersections.get(problem_id, 0) + 1

            closest_id: str | None = None
            max_similarity = 0.0
            candidate_size = len(candidate_shingles)
            for problem_id, intersection_size in intersections.items():
                existing_size = len(self._documents[problem_id])
                union_size = candidate_size + existing_size - intersection_size
                similarity = intersection_size / union_size if union_size else 0.0
                if similarity > max_similarity:
                    closest_id = problem_id
                    max_similarity = similarity
            return NoveltyResult(
                passed=max_similarity < threshold,
                max_similarity=max_similarity,
                closest_id=closest_id,
            )

    def check_exact(self, candidate: str) -> NoveltyResult:
        """Reject an accepted artifact duplicate while retaining numeric values."""
        with self._lock:
            fingerprint = _artifact_fingerprint(candidate)
            closest_id = next(iter(self._artifact_postings.get(fingerprint, ())), None)
            return NoveltyResult(
                passed=closest_id is None,
                max_similarity=1.0 if closest_id else 0.0,
                closest_id=closest_id,
                mode="exact_variant",
            )

    def check_variant(
        self,
        candidate: str,
        threshold: float,
        *,
        parent_id: str | None,
        exact_only: bool,
    ) -> NoveltyResult:
        """Apply lineage-aware novelty without defeating controlled variants."""
        with self._lock:
            exact = self.check_exact(candidate)
            if not exact.passed or exact_only:
                return exact
            result = self.check(
                candidate,
                threshold,
                exclude_ids=frozenset({parent_id}) if parent_id else frozenset(),
            )
            return NoveltyResult(
                passed=result.passed,
                max_similarity=result.max_similarity,
                closest_id=result.closest_id,
                mode="derived_blueprint",
            )

    def add(self, problem_id: str, latex: str) -> None:
        with self._lock:
            self._remove_unlocked(problem_id)
            shingles = _shingles(latex)
            fingerprint = _artifact_fingerprint(latex)
            self._documents[problem_id] = shingles
            self._artifact_fingerprints[problem_id] = fingerprint
            self._artifact_postings.setdefault(fingerprint, set()).add(problem_id)
            if not shingles:
                self._empty_documents.add(problem_id)
                return
            for shingle in shingles:
                self._postings.setdefault(shingle, set()).add(problem_id)

    def check_and_add(
        self,
        problem_id: str,
        latex: str,
        threshold: float,
        *,
        exclude_ids: set[str] | frozenset[str] = frozenset(),
    ) -> NoveltyResult:
        """Atomically reject or register a candidate for parallel workers."""
        with self._lock:
            result = self.check(latex, threshold, exclude_ids=exclude_ids)
            if result.passed:
                self.add(problem_id, latex)
            return result

    def check_variant_and_add(
        self,
        problem_id: str,
        latex: str,
        threshold: float,
        *,
        parent_id: str | None,
        exact_only: bool,
    ) -> NoveltyResult:
        """Atomically apply variant-aware novelty and register accepted source."""
        with self._lock:
            result = self.check_variant(
                latex,
                threshold,
                parent_id=parent_id,
                exact_only=exact_only,
            )
            if result.passed:
                self.add(problem_id, latex)
            return result

    def remove(self, problem_id: str) -> None:
        with self._lock:
            self._remove_unlocked(problem_id)

    def _remove_unlocked(self, problem_id: str) -> None:
        shingles = self._documents.pop(problem_id, None)
        self._empty_documents.discard(problem_id)
        fingerprint = self._artifact_fingerprints.pop(problem_id, None)
        if fingerprint is not None:
            exact_posting = self._artifact_postings.get(fingerprint)
            if exact_posting is not None:
                exact_posting.discard(problem_id)
                if not exact_posting:
                    del self._artifact_postings[fingerprint]
        if not shingles:
            return
        for shingle in shingles:
            posting = self._postings.get(shingle)
            if posting is None:
                continue
            posting.discard(problem_id)
            if not posting:
                del self._postings[shingle]

    def __len__(self) -> int:
        with self._lock:
            return len(self._documents)
