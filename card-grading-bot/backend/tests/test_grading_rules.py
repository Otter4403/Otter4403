import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.grading.base import (
    SubGrades, centering_score_linear, piecewise_centering_score, worst_axis_pct, threshold_lookup,
)
from app.grading.psa import grade_psa
from app.grading.beckett import grade_beckett
from app.grading.cgc import grade_cgc
from app.grading.tag import grade_tag
from app.grading.sgc import grade_sgc
from app.grading.hga import grade_hga


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


def test_threshold_lookup_picks_first_met_threshold_and_falls_back_to_lowest():
    table = [(9.0, "high"), (5.0, "mid"), (1.0, "low")]
    assert threshold_lookup(9.5, table) == "high"
    assert threshold_lookup(7.0, table) == "mid"
    assert threshold_lookup(0.0, table) == "low"


def test_sgc_perfect_card_grades_100_pristine():
    result = grade_sgc(perfect_subgrades())
    assert result.overall == 100
    assert result.label == "Pristine"
    assert result.scale.startswith("10-100")


def test_sgc_weakest_link_caps_grade():
    result = grade_sgc(flawed_subgrades())
    # corners=6 is the worst input attribute -> should land well below the top of the scale
    assert result.overall <= 70


def test_hga_perfect_card_grades_ten_with_hundredth_precision():
    result = grade_hga(perfect_subgrades())
    assert result.overall == 10.0
    assert result.scale.startswith("1.00")


def test_hga_uses_per_corner_and_per_edge_detail_when_available():
    sg = SubGrades(
        centering_lr=(50.0, 50.0),
        centering_tb=(50.0, 50.0),
        corners=9.0,
        edges=9.0,
        surface=9.0,
        corner_details={"top_left": 5.0, "top_right": 9.0, "bottom_left": 9.0, "bottom_right": 9.0},
        edge_details={"top": 9.0, "bottom": 9.0, "left": 9.0, "right": 9.0},
    )
    result = grade_hga(sg)
    assert result.subgrades["corner_top_left"] == 5.0
    uniform = grade_hga(perfect_subgrades())
    assert result.overall < uniform.overall


def test_all_graders_stay_within_their_scale():
    for grader in (grade_psa, grade_beckett, grade_cgc, grade_tag, grade_hga):
        result = grader(flawed_subgrades())
        assert 1 <= result.overall <= 10
    sgc_result = grade_sgc(flawed_subgrades())
    assert 10 <= sgc_result.overall <= 100


def test_piecewise_centering_score_interpolates_between_anchors():
    table = [(50.0, 10.0), (60.0, 8.0), (100.0, 0.0)]
    assert piecewise_centering_score(50.0, table, granularity=0.1) == 10.0
    assert piecewise_centering_score(55.0, table, granularity=0.1) == 9.0  # midpoint of 50->60
    assert piecewise_centering_score(60.0, table, granularity=0.1) == 8.0
    # clamps outside the published range instead of extrapolating past it
    assert piecewise_centering_score(40.0, table, granularity=0.1) == 10.0
    assert piecewise_centering_score(150.0, table, granularity=0.1) == 0.0


def test_psa_centering_matches_published_breakpoints():
    def sg_with_front(worst_lr):
        return SubGrades(centering_lr=(worst_lr, 100 - worst_lr), centering_tb=(50.0, 50.0),
                          corners=10.0, edges=10.0, surface=10.0)

    assert grade_psa(sg_with_front(55.0)).subgrades["centering"] == 10
    assert grade_psa(sg_with_front(60.0)).subgrades["centering"] == 9
    assert grade_psa(sg_with_front(65.0)).subgrades["centering"] == 8
    assert grade_psa(sg_with_front(70.0)).subgrades["centering"] == 7


def test_psa_bad_back_centering_caps_grade_even_with_perfect_front():
    sg = SubGrades(
        centering_lr=(50.0, 50.0), centering_tb=(50.0, 50.0),
        back_centering_lr=(95.0, 5.0), back_centering_tb=(50.0, 50.0),
        corners=10.0, edges=10.0, surface=10.0,
    )
    result = grade_psa(sg)
    assert result.overall < 10


def test_sgc_centering_matches_published_breakpoints():
    def sg_with_front(worst_lr):
        return SubGrades(centering_lr=(worst_lr, 100 - worst_lr), centering_tb=(50.0, 50.0),
                          corners=10.0, edges=10.0, surface=10.0)

    assert grade_sgc(sg_with_front(50.0)).overall == 100
    assert grade_sgc(sg_with_front(55.0)).overall == 98
    assert grade_sgc(sg_with_front(60.0)).overall == 96


def test_tag_has_no_9point5_and_uses_pristine_gem_mint_qualifiers():
    from app.grading.tag import _tag_score_to_grade
    assert _tag_score_to_grade(989) == (10.0, "Gem Mint")
    assert _tag_score_to_grade(990) == (10.0, "Pristine")
    assert _tag_score_to_grade(950) == (10.0, "Gem Mint")
    assert _tag_score_to_grade(949) == (9.0, "Mint")
    # confirm no value of tag_score can ever produce a 9.5 grade
    for score in range(100, 1001):
        grade, _ = _tag_score_to_grade(score)
        assert grade != 9.5


def test_tag_bad_back_centering_caps_grade_even_with_perfect_front():
    sg = SubGrades(
        centering_lr=(50.0, 50.0), centering_tb=(50.0, 50.0),
        back_centering_lr=(95.0, 5.0), back_centering_tb=(50.0, 50.0),
        corners=10.0, edges=10.0, surface=10.0,
    )
    result = grade_tag(sg)
    assert result.overall < 10.0


def test_companies_diverge_on_a_near_perfect_but_not_perfect_card():
    # A card that's a true 10 on 4 of the 5 attributes but 9.9 on corners
    # should still show up as a perfect 10 on the coarser scales (PSA whole
    # numbers, BGS/CGC half points, TAG tenths) while the finer-grained
    # scales (SGC's 2-point steps near the top, HGA's hundredths) reflect
    # the imperfection -- this divergence is the whole point of comparing
    # multiple companies on the same card.
    sg = SubGrades(
        centering_lr=(50.0, 50.0),
        centering_tb=(50.0, 50.0),
        corners=9.9,
        edges=10.0,
        surface=10.0,
    )
    assert grade_psa(sg).overall == 10
    assert grade_beckett(sg).overall == 10
    assert grade_cgc(sg).overall == 10
    assert grade_tag(sg).overall == 10.0
    assert grade_sgc(sg).overall < 100
    assert grade_hga(sg).overall < 10.0
