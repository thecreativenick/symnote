import random
from fractions import Fraction

import pytest

from symnote import Num, ParseError, Sym, diff, evaluate, parse

x, y = Sym("x"), Sym("y")


def test_like_terms_combine():
    assert x + x == 2 * x
    assert x * x == x ** 2
    assert x - x == Num(0)
    assert x * x ** -1 == Num(1)


def test_constants_fold_exactly():
    assert parse("1/3 + 1/6") == Num(Fraction(1, 2))


def test_order_does_not_matter():
    assert parse("y + 2*x + 1") == parse("1 + x*2 + y")
    assert parse("x*y*x") == parse("y*x**2")


def test_parse_precedence():
    assert parse("-x**2") == -(x ** 2)
    assert parse("2**3**2") == Num(512)
    assert parse("(x + 1)*(x - 1)") == (x + 1) * (x - 1)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("x**3", "3*x**2"),
        ("5*x**2 + 3*x + 7", "3 + 10*x"),
        ("x*y", "y"),
        ("1/x", "-x**(-2)"),
        ("42", "0"),
    ],
)
def test_derivatives(text, expected):
    assert diff(parse(text), x) == parse(expected)


def test_derivative_matches_finite_difference():
    rng = random.Random(1)
    e = parse("(x**2 + 3*x*y) * (x - y)**3 / (x + 2)")
    d = diff(e, x)
    for _ in range(20):
        env = {"x": Fraction(rng.randint(1, 9), 3), "y": Fraction(rng.randint(-9, 9), 4)}
        h = Fraction(1, 10**8)
        numeric = (evaluate(e, {**env, "x": env["x"] + h}) - evaluate(e, {**env, "x": env["x"] - h})) / (2 * h)
        assert abs(float(numeric - evaluate(d, env))) < 1e-6


def test_printing():
    assert str(parse("3*x**2 - x + 1")) == "1 - x + 3*x**2"


def test_parse_errors():
    with pytest.raises(ParseError):
        parse("x +")
    with pytest.raises(ParseError):
        parse("x $ y")
