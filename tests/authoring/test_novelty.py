from vbagent.authoring.novelty import (
    NoveltyIndex,
    blueprint_similarity,
    variant_stem_similarity,
)


def test_indexed_novelty_matches_exact_pairwise_similarity():
    documents = {
        "one": r"\item A block of mass 2 kg slides down a rough incline.",
        "two": r"\item A charged bead moves through a uniform magnetic field.",
        "three": r"\item Find the time period of a spring mass oscillator.",
    }
    candidate = r"\item A block of mass 8 kg slides down a rough incline."
    index = NoveltyIndex()
    for problem_id, latex in documents.items():
        index.add(problem_id, latex)

    result = index.check(candidate, threshold=0.88)
    expected_id, expected = max(
        (
            (problem_id, blueprint_similarity(candidate, latex))
            for problem_id, latex in documents.items()
        ),
        key=lambda pair: pair[1],
    )

    assert result.closest_id == expected_id
    assert result.max_similarity == expected
    assert result.passed is (expected < 0.88)


def test_check_and_add_is_accepted_only_and_remove_is_complete():
    index = NoveltyIndex()
    original = r"\item Determine the acceleration of the cart on the incline."
    duplicate = r"\item Determine the acceleration of the cart on the incline."

    assert index.check_and_add("first", original, 0.88).passed
    assert not index.check_and_add("duplicate", duplicate, 0.88).passed
    assert len(index) == 1

    index.remove("first")
    assert index.check(duplicate, 0.88).passed
    assert len(index) == 0


def test_numerical_variant_uses_exact_uniqueness_not_blueprint_novelty():
    index = NoveltyIndex()
    parent = r"\item A 2 kg block slides 4 m down an incline."
    child = r"\item A 3 kg block slides 8 m down an incline."
    index.add("parent", parent)

    assert not index.check(child, 0.88).passed
    accepted = index.check_variant_and_add(
        "child",
        child,
        0.88,
        parent_id="parent",
        exact_only=True,
    )
    assert accepted.passed
    assert accepted.mode == "exact_variant"

    duplicate = index.check_variant(
        child,
        0.88,
        parent_id="parent",
        exact_only=True,
    )
    assert not duplicate.passed
    assert duplicate.closest_id == "child"


def test_variant_stem_similarity_ignores_numbers_and_option_churn():
    parent = (
        r"\item A particle is projected at 10 \mathrm{m/s}. Find its range."
        r"\begin{tasks}(2)\task 5\task 10\task 15\task 20\end{tasks}"
    )
    numerical = (
        r"\item A particle is projected at 14 \text{ms}^{-1}. Find its range."
        r"\begin{tasks}(2)\task 28\task 14\task 7\task 21\end{tasks}"
    )
    contextual = (
        r"\item A car brakes on a wet road at 14 \text{ms}^{-1}. Find its stopping distance."
        r"\begin{tasks}(2)\task 28\task 14\task 7\task 21\end{tasks}"
    )

    assert variant_stem_similarity(parent, numerical) >= 0.90
    assert variant_stem_similarity(parent, contextual) < 0.90
