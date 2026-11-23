"""Immutable expression trees with automatic simplification on construction.

Canonical forms kept by the constructors:
- numbers are exact ``Fraction`` values;
- ``Add``/``Mul`` are flattened, constants are folded, and like terms/factors are combined
  (``x + x -> 2*x``, ``x * x -> x**2``);
- arguments are sorted by (kind rank, printed form) so equal expressions compare equal.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping


class Expr:
    def __add__(self, other): return add(self, as_expr(other))
    def __radd__(self, other): return add(as_expr(other), self)
    def __sub__(self, other): return add(self, mul(Num(-1), as_expr(other)))
    def __rsub__(self, other): return add(as_expr(other), mul(Num(-1), self))
    def __mul__(self, other): return mul(self, as_expr(other))
    def __rmul__(self, other): return mul(as_expr(other), self)
    def __truediv__(self, other): return mul(self, power(as_expr(other), Num(-1)))
    def __rtruediv__(self, other): return mul(as_expr(other), power(self, Num(-1)))
    def __pow__(self, other): return power(self, as_expr(other))
    def __neg__(self): return mul(Num(-1), self)

    def sort_key(self) -> tuple:
        raise NotImplementedError


@dataclass(frozen=True)
class Num(Expr):
    value: Fraction

    def __init__(self, value):
        object.__setattr__(self, "value", Fraction(value))

    def sort_key(self): return (0, self.value)
    def __str__(self): return str(self.value)


@dataclass(frozen=True)
class Sym(Expr):
    name: str

    def sort_key(self): return (1, self.name)
    def __str__(self): return self.name


@dataclass(frozen=True)
class Add(Expr):
    terms: tuple[Expr, ...]

    def sort_key(self): return (3, str(self))
    def __str__(self): return " + ".join(_paren(t, Add) for t in self.terms).replace("+ -", "- ")


@dataclass(frozen=True)
class Mul(Expr):
    factors: tuple[Expr, ...]

    def sort_key(self): return (2, str(self))

    def __str__(self):
        if isinstance(self.factors[0], Num) and self.factors[0].value == -1:
            return "-" + str(Mul(self.factors[1:]) if len(self.factors) > 2 else self.factors[1])
        return "*".join(_paren(f, Mul) for f in self.factors)


@dataclass(frozen=True)
class Pow(Expr):
    base: Expr
    exp: Expr

    def sort_key(self): return (2, str(self))
    def __str__(self): return f"{_paren(self.base, Pow)}**{_paren(self.exp, Pow)}"


def _paren(e: Expr, parent: type) -> str:
    rank = {Add: 1, Mul: 2, Pow: 3}
    inner = rank.get(type(e), 4)
    if isinstance(e, Num) and (e.value < 0 or e.value.denominator != 1):
        inner = 1
    return f"({e})" if inner <= rank[parent] else str(e)


def as_expr(x) -> Expr:
    if isinstance(x, Expr):
        return x
    if isinstance(x, (int, Fraction)):
        return Num(x)
    raise TypeError(f"cannot convert {x!r} to an expression")


ZERO, ONE = Num(0), Num(1)


def _split_coeff(term: Expr) -> tuple[Fraction, Expr]:
    """3*x*y -> (3, x*y)."""
    if isinstance(term, Num):
        return term.value, ONE
    if isinstance(term, Mul) and isinstance(term.factors[0], Num):
        rest = term.factors[1:]
        return term.factors[0].value, rest[0] if len(rest) == 1 else Mul(rest)
    return Fraction(1), term


def add(*args: Expr) -> Expr:
    flat: list[Expr] = []
    for a in args:
        flat.extend(a.terms if isinstance(a, Add) else (a,))
    const = Fraction(0)
    coeffs: dict[Expr, Fraction] = {}
    for t in flat:
        c, base = _split_coeff(t)
        if base == ONE:
            const += c
        else:
            coeffs[base] = coeffs.get(base, Fraction(0)) + c
    terms = [mul(Num(c), b) for b, c in coeffs.items() if c != 0]
    terms.sort(key=lambda e: e.sort_key())
    if const != 0:
        terms.insert(0, Num(const))
    if not terms:
        return ZERO
    return terms[0] if len(terms) == 1 else Add(tuple(terms))


def mul(*args: Expr) -> Expr:
    flat: list[Expr] = []
    for a in args:
        flat.extend(a.factors if isinstance(a, Mul) else (a,))
    const = Fraction(1)
    exps: dict[Expr, Expr] = {}
    for f in flat:
        if isinstance(f, Num):
            const *= f.value
            continue
        base, e = (f.base, f.exp) if isinstance(f, Pow) else (f, ONE)
        exps[base] = add(exps[base], e) if base in exps else e
    if const == 0:
        return ZERO
    factors = [power(b, e) for b, e in exps.items()]
    factors = [f for f in factors if f != ONE]
    factors.sort(key=lambda e: e.sort_key())
    if const != 1 or not factors:
        factors.insert(0, Num(const))
    return factors[0] if len(factors) == 1 else Mul(tuple(factors))


def power(base: Expr, exp: Expr) -> Expr:
    if exp == ZERO:
        return ONE
    if exp == ONE:
        return base
    if base == ONE:
        return ONE
    if isinstance(base, Num) and isinstance(exp, Num) and exp.value.denominator == 1:
        if base.value == 0 and exp.value < 0:
            raise ZeroDivisionError("0 raised to a negative power")
        return Num(base.value ** int(exp.value))
    if isinstance(base, Pow) and isinstance(exp, Num) and exp.value.denominator == 1:
        return power(base.base, mul(base.exp, exp))  # (x**a)**n = x**(a*n) for integer n
    return Pow(base, exp)


def diff(e: Expr, x: Sym) -> Expr:
    """Derivative of ``e`` with respect to ``x``."""
    if isinstance(e, Num):
        return ZERO
    if isinstance(e, Sym):
        return ONE if e == x else ZERO
    if isinstance(e, Add):
        return add(*(diff(t, x) for t in e.terms))
    if isinstance(e, Mul):  # product rule
        parts = []
        for i, f in enumerate(e.factors):
            df = diff(f, x)
            if df != ZERO:
                parts.append(mul(*e.factors[:i], df, *e.factors[i + 1:]))
        return add(*parts) if parts else ZERO
    if isinstance(e, Pow):
        if diff(e.exp, x) != ZERO:
            raise NotImplementedError("variable exponents need exp/log support")
        return mul(e.exp, power(e.base, add(e.exp, Num(-1))), diff(e.base, x))
    raise TypeError(f"unknown expression {e!r}")


def evaluate(e: Expr, env: Mapping[str, Fraction | int | float]) -> Fraction | float:
    if isinstance(e, Num):
        return e.value
    if isinstance(e, Sym):
        return env[e.name]
    if isinstance(e, Add):
        return sum((evaluate(t, env) for t in e.terms), Fraction(0))
    if isinstance(e, Mul):
        out = Fraction(1)
        for f in e.factors:
            out = out * evaluate(f, env)
        return out
    if isinstance(e, Pow):
        b, p = evaluate(e.base, env), evaluate(e.exp, env)
        if isinstance(p, Fraction) and p.denominator == 1:
            return b ** int(p)
        return float(b) ** float(p)
    raise TypeError(f"unknown expression {e!r}")
