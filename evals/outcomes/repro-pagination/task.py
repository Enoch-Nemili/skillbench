"""A symptom-only bug report (no numbers to copy). Graded by running the answer's code."""

from skillbench.grading import code_check_suite

SKILL = "repro-before-fix"

BUGGY = '''\
def paginate(items, page, size):
    """Return page number `page` (1 = first page) of `items`, `size` items per page."""
    start = page * size
    return items[start:start + size]
'''

HIDDEN_TESTS = """\
from paginator import paginate

ITEMS = list(range(25))


def test_first_page():
    assert paginate(ITEMS, 1, 10) == list(range(10))


def test_middle_page():
    assert paginate(ITEMS, 2, 10) == list(range(10, 20))


def test_last_partial_page():
    assert paginate(ITEMS, 3, 10) == [20, 21, 22, 23, 24]


def test_past_the_end():
    assert paginate(ITEMS, 4, 10) == []


def test_other_size():
    assert paginate(ITEMS, 1, 7) == list(range(7))
"""

PROMPT = f"""
Users say the top search results never show up: the first page of results starts somewhere in
the middle of the list. Here's paginator.py. Please sort it out.

```python
# file: paginator.py
{BUGGY}```
"""


def grade(output: str):
    return code_check_suite(output, "paginator.py", BUGGY, HIDDEN_TESTS)
