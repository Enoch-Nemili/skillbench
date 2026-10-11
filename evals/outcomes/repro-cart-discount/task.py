"""A pricing bug with a precise report. Graded by running the answer's code."""

from skillbench.grading import code_check_suite

SKILL = "repro-before-fix"

BUGGY = '''\
def cart_total(items, discount_code=None):
    """items: list of (unit_price, quantity).

    SAVE10 takes 10% off the subtotal. Tax is 8%, charged on the discounted subtotal.
    Returns the total rounded to cents.
    """
    subtotal = sum(price * qty for price, qty in items)
    total = subtotal * 1.08
    if discount_code == "SAVE10":
        total = total - subtotal * 0.10
    return round(total, 2)
'''

HIDDEN_TESTS = """\
from cart import cart_total


def test_no_code():
    assert cart_total([(50, 2)]) == 108.0


def test_save10_on_100():
    assert cart_total([(50, 2)], "SAVE10") == 97.2


def test_save10_mixed_items():
    assert cart_total([(19.99, 3), (5, 1)], "SAVE10") == round((19.99 * 3 + 5) * 0.9 * 1.08, 2)


def test_unknown_code_is_ignored():
    assert cart_total([(50, 2)], "BOGUS") == 108.0


def test_empty_cart():
    assert cart_total([], "SAVE10") == 0
"""

PROMPT = f"""
Customers say carts using the SAVE10 code are overcharged. A $100 cart should come to $97.20
(10% off, then 8% tax), but checkout shows $98.00. Here's cart.py. Can you fix it?

```python
# file: cart.py
{BUGGY}```
"""


def grade(output: str):
    return code_check_suite(output, "cart.py", BUGGY, HIDDEN_TESTS)
