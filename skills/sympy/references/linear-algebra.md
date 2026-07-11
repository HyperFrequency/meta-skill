# SymPy Matrices and Linear Algebra

Symbolic (and small numeric) linear algebra. Every operation below works with
symbolic entries. For large numeric matrices, `lambdify` to NumPy instead.

## Construction

```python
from sympy import Matrix, eye, zeros, ones, diag
M = Matrix([[1, 2], [3, 4]])     # from rows
v = Matrix([1, 2, 3])            # column vector
r = Matrix([[1, 2, 3]])          # row vector
eye(3)                           # 3x3 identity
zeros(2, 3)                      # 2x3 of zeros
ones(3, 2)                       # 3x2 of ones
diag(1, 2, 3)                    # diagonal matrix
```

`Matrix.hstack(A, B, ...)` and `Matrix.vstack(...)` concatenate blocks.
`BlockDiagMatrix(A, B)` builds a block-diagonal matrix.

## Shape, Access, Modification

```python
M.shape           # (rows, cols)
M.rows, M.cols
M[0, 0]           # element (0-indexed)
M[0, :]           # row 0 as a matrix   (M.row(0))
M[:, 1]           # column 1 as a matrix (M.col(1))
M[0:2, 0:2]       # submatrix slice
M.row_insert(1, Matrix([[5, 6]]))
M.col_insert(1, Matrix([7, 8]))
M.row_del(0); M.col_del(1)        # return-new in modern SymPy
```

`Matrix` is mutable; `ImmutableMatrix` is hashable (usable as dict keys / inside
other expressions).

## Arithmetic

```python
A + B            # addition
2 * A            # scalar multiply
A * B            # matrix product
A**2             # A*A;  A**-1 is the inverse
A.multiply_elementwise(B)   # Hadamard product
A.T              # transpose
A.conjugate()    # elementwise conjugate
A.H              # conjugate (Hermitian) transpose
```

## Core Quantities

```python
M.det()                  # determinant (symbolic-friendly)
M.trace()                # sum of diagonal
M.inv()                  # inverse (or M**-1); raises if singular
M.is_invertible()
rref_M, pivots = M.rref()  # reduced row-echelon form + pivot columns
M.rank()
M.nullspace()            # list of basis vectors for the kernel
M.columnspace()          # basis for the column space
M.rowspace()             # basis for the row space
```

Gram-Schmidt: `Matrix.orthogonalize(*vectors, normalize=True)`.

## Eigenproblems

```python
M.eigenvals()            # {eigenvalue: algebraic multiplicity}
M.eigenvects()           # [(eigenvalue, multiplicity, [eigenvectors]), ...]
M.is_diagonalizable()
P, D = M.diagonalize()   # M == P * D * P**-1, D diagonal
M.charpoly(lam).as_expr()  # characteristic polynomial in symbol `lam`
P, J = M.jordan_form()   # Jordan normal form for non-diagonalizable M
```

## Decompositions

```python
L, U, perm = M.LUdecomposition()   # LU with row permutation
Q, R = M.QRdecomposition()         # QR
L = M.cholesky()                   # M == L * L.T (SPD matrices)
U, S, V = M.singular_value_decomposition()   # M == U * S * V
```

Decompositions with symbolic entries can be large; simplify or substitute
numeric values when they blow up.

## Solving Linear Systems

```python
A = Matrix([[1, 2], [3, 4]]); b = Matrix([5, 6])
A.solve(b)                    # exact solve (square, nonsingular)
A.solve_least_squares(b)      # overdetermined / least squares
A.gauss_jordan_solve(b)       # general; returns solution + free params
```

Or with `linsolve` (returns a solution Set, handles under/over-determined):

```python
from sympy import linsolve, symbols
x, y = symbols('x y')
linsolve([x + y - 5, 2*x - y - 1], [x, y])            # equations
linsolve(Matrix([[1, 1, 5], [2, -1, 1]]), [x, y])     # augmented matrix
linsolve((A, b), [x, y])                              # A x = b tuple
```

## Symbolic Entries and Matrix Functions

```python
from sympy import symbols, exp, sin, Matrix
a, b, c, d = symbols('a b c d')
M = Matrix([[a, b], [c, d]])
M.det()      # a*d - b*c
M.inv()      # closed-form symbolic inverse
M.eigenvals()  # symbolic eigenvalues

R = Matrix([[0, 1], [-1, 0]])
exp(R)       # matrix exponential
```

`MatrixSymbol('A', m, n)` creates an abstract m×n matrix for expression-level
manipulation before assigning concrete entries.

## Sparse Matrices

```python
from sympy import SparseMatrix
S = SparseMatrix(1000, 1000, {(0, 0): 1, (100, 100): 2})  # stores nonzeros only
SparseMatrix(Matrix([[1, 0, 0], [0, 2, 0]]))              # densify -> sparse
```

## Useful Patterns

```python
# Projection onto the column space of A
P = A * (A.T * A).inv() * A.T

# Change of basis: express v (old basis) in a new basis whose columns are new_*
Pmat = Matrix.hstack(Matrix([1, 1]), Matrix([1, -1]))
v_new = Pmat.inv() * Matrix([3, 4])
```

## Notes and Caveats

- **Zero-testing** of complicated symbolic entries can be unreliable and affects
  `rank`, `rref`, and `inv`. Simplify entries or substitute numerics if results
  look wrong.
- **Performance**: symbolic operations on large matrices are expensive. For
  numeric work, `lambdify` the symbolic result to NumPy and use `numpy.linalg`.
- **Assumptions** on the symbols (`real=True`, `positive=True`) help
  simplification of determinants, inverses, and eigenvalues.
