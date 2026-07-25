"""Runs one set of condition measurements through every supported company's
grading rules and returns all results together."""

from typing import Dict, List

from .base import GradeResult, SubGrades
from .psa import grade_psa
from .beckett import grade_beckett
from .cgc import grade_cgc
from .tag import grade_tag
from .sgc import grade_sgc
from .hga import grade_hga

GRADERS = {
    "psa": grade_psa,
    "bgs": grade_beckett,
    "cgc": grade_cgc,
    "tag": grade_tag,
    "sgc": grade_sgc,
    "hga": grade_hga,
}


def grade_all(sg: SubGrades) -> Dict[str, GradeResult]:
    return {key: grader(sg) for key, grader in GRADERS.items()}


def grade_all_as_dicts(sg: SubGrades) -> List[Dict]:
    return [result.to_dict() for result in grade_all(sg).values()]
