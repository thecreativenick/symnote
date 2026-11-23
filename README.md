# symnote

A computer algebra system written from scratch, with a browser notebook. Type an integral and
get the exact answer, typeset.

## Status

Early scaffold. Done so far:

- Immutable expression trees (`Num`, `Sym`, `Add`, `Mul`, `Pow`) with exact rational numbers
  and canonical simplification on construction (flattening, constant folding, like terms).
- A parser for `+ - * / ** ^` and parentheses.
- Differentiation for polynomials and rational expressions, checked against finite differences.

## Planned milestones

1. Functions (`sin`, `cos`, `exp`, `log`, `sqrt`) and their derivatives.
2. Polynomials: expansion, division, GCD, factoring over the rationals.
3. Equation solving: linear and polynomial equations, small systems.
4. Integration: table lookup, substitution, parts, rational functions via partial fractions.
5. LaTeX output and a localhost notebook page with typeset answers and plots.

## Success bar

Answers to 500 problems agree with SymPy, used only as a checker, at random points, and a
scripted Playwright session in the notebook passes.

## Development

```bash
pip install -e .[dev]
pytest
```
