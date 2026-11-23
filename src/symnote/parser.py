"""Parse text like ``3*x**2 - (y + 1)/2`` into expression trees (precedence climbing)."""

from __future__ import annotations

import re
from fractions import Fraction

from .expr import Expr, Num, Sym, power

_TOKEN = re.compile(r"\s*(?:(\d+(?:\.\d+)?)|([A-Za-z_]\w*)|(\*\*|[-+*/^()]))")


class ParseError(ValueError):
    pass


def _tokenize(text: str) -> list[str]:
    tokens, pos = [], 0
    text = text.rstrip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m:
            raise ParseError(f"unexpected character {text[pos]!r} at {pos}")
        tokens.append(m.group(m.lastindex))
        pos = m.end()
    return tokens


class _Parser:
    def __init__(self, tokens: list[str]):
        self.tokens, self.i = tokens, 0

    def peek(self) -> str | None:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def take(self) -> str:
        tok = self.peek()
        if tok is None:
            raise ParseError("unexpected end of input")
        self.i += 1
        return tok

    def expr(self) -> Expr:  # sum := term (('+'|'-') term)*
        left = self.term()
        while self.peek() in ("+", "-"):
            op, right = self.take(), self.term()
            left = left + right if op == "+" else left - right
        return left

    def term(self) -> Expr:  # term := unary (('*'|'/') unary)*
        left = self.unary()
        while self.peek() in ("*", "/"):
            op, right = self.take(), self.unary()
            left = left * right if op == "*" else left / right
        return left

    def unary(self) -> Expr:
        if self.peek() == "-":
            self.take()
            return -self.unary()
        if self.peek() == "+":
            self.take()
            return self.unary()
        return self.pow()

    def pow(self) -> Expr:  # right-associative, binds tighter than unary minus on the left
        base = self.atom()
        if self.peek() in ("**", "^"):
            self.take()
            return power(base, self.unary())
        return base

    def atom(self) -> Expr:
        tok = self.take()
        if tok == "(":
            inner = self.expr()
            if self.take() != ")":
                raise ParseError("expected ')'")
            return inner
        if tok[0].isdigit():
            return Num(Fraction(tok))
        if tok[0].isalpha() or tok[0] == "_":
            return Sym(tok)
        raise ParseError(f"unexpected token {tok!r}")


def parse(text: str) -> Expr:
    p = _Parser(_tokenize(text))
    result = p.expr()
    if p.peek() is not None:
        raise ParseError(f"unexpected token {p.peek()!r}")
    return result
