import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.grading.base import SubGrades, centering_score_linear, worst_axis_pct
from app.grading.psa import grade_psa
from app.grading.beckett import grade_beckett
from app.grading.cgc import grade_cgc
from app.grading.tag import grade_tag


def perfect_subgrades():
    return SubGrades(
        centering_lr=(50.0, 50.0),
        centering_tb=(50.0, 50.0),
        corners=10.0,
        edges=10.0,
        surface=10.0,
    )


def flawed_subgrades():
    return SubGrades(
        centering_lr=(58.0, 42.0),
        centering_tb=(52.0, 48.0),
        corners=6.0,
        edges=8.0,
        surface=9.0,
    )


def test_worst_axis_pct():
    assert worst_axis_pct((50, 50)) == 50.0
    assert worst_axis_pct((60, 40)) == 60.0
    assert worst_axis_pct((40, 60)) == 60.0


def test_centering_score_linear_bounds():
    assert centering_score_linear(50, granularity=1) == 10
    assert centering_score_linear(95, granularity=1) == 1
    assert centering_score_linear(150, granularity=1) == 1  # clamps beyond floor
    assert centering_score_linear(40, granularity=1) == 10  # clamps below perfect


def test_psa_perfect_card_grades_gem_mint_10():
    result = grade_psa(perfect_subgrades())
    assert result.overall == 10
    assert result.label == "Gem Mint"


def test_psa_weakest_link_caps_grade():
    result = grade_psa(flawed_subgrades())
    # corners=6 is the worst input attribute -> should cap (or nearly cap) the grade
    assert result.overall <= 7
    assert result.overall == min(result.subgrades.values())


def test_beckett_perfect_card_is_black_label_10():
    result = grade_beckett(perfect_subgrades())
    assert result.overall == 10
    assert "Black Label" in result.label


def test_beckett_overall_never_exceeds_min_subgrade_by_more_than_gap():
    result = grade_beckett(flawed_subgrades())
    min_sub = min(result.subgrades.values())
    assert result.overall <= min_sub + 1.0 + 1e-9


def test_cgc_perfect_card_grades_ten():
    result = grade_cgc(perfect_subgrades())
    assert result.overall == 10


def test_cgc_overall_within_gap_of_min_subgrade():
    result = grade_cgc(flawed_subgrades())
    min_sub = min(result.subgrades.values())
    assert result.overall <= min_sub + 1.5 + 1e-9


def test_tag_perfect_card_grades_ten_with_decimal_scale():
    result = grade_tag(perfect_subgrades())
    assert result.overall == 10.0
    assert result.scale.startswith("1.0")


def test_tag_uses_per_corner_and_per_edge_detail_when_available():
    sg = SubGrades(
        centering_lr=(50.0, 50.0),
        centering_tb=(50.0, 50.0),
        corners=9.0,
        edges=9.0,
        surface=9.0,
        corner_details={"top_left": 5.0, "top_right": 9.0, "bottom_left": 9.0, "bottom_right": 9.0},
        edge_details={"top": 9.0, "bottom": 9.0, "left": 9.0, "right": 9.0},
    )
    result = grade_tag(sg)
    assert result.subgrades["corner_top_left"] == 5.0
    # the weak corner should pull the overall below a card with uniformly strong corners
    uniform = grade_tag(perfect_subgrades())
    assert result.overall < uniform.overall


def test_all_graders_stay_within_their_scale():
    for grader in (grade_psa, grade_beckett, grade_cgc, grade_tag):
        result = grader(flawed_subgrades())
        assert 1 <= result.overall <= 10
