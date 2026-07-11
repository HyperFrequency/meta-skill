# Matrices and Arrays

The array is MATLAB's primitive type. Indexing is 1-based and storage is
column-major, which governs linear indexing and reshape order.

## Creating arrays

```matlab
A = [1 2 3; 4 5 6];      % rows separated by ; , columns by space or comma
row = [1, 2, 3];          % 1x3
col = [1; 2; 3];          % 3x1

% Ranges
1:10                      % step 1
0:0.5:5                   % explicit step
10:-1:1                   % descending
linspace(0, 1, 100)       % 100 evenly spaced points, endpoints included
logspace(0, 3, 50)        % 50 points from 10^0 to 10^3
```

### Constructors

```matlab
eye(n)            eye(m, n)        % identity
zeros(m, n)       ones(m, n)       % constant fill
diag([1 2 3])                      % build diagonal matrix from vector
diag(A)                            % extract diagonal as vector
rand(m, n)        randn(m, n)      % uniform [0,1] / standard normal
randi([lo hi], m, n)               % random integers
randperm(n)                        % permutation of 1:n
true(m, n)        false(m, n)      % logical fills
zeros(size(B))                     % match another array's shape
ones(size(B), 'like', B)           % match shape AND type
```

### Grids

```matlab
[X, Y] = meshgrid(x, y);       % meshgrid: X varies across columns
[X, Y, Z] = meshgrid(x, y, z);
[X, Y] = ndgrid(x, y);         % ndgrid: X varies down rows (transposed layout)
```

Pick `meshgrid` for `surf`/`contour` plotting; `ndgrid` for N-D interpolation
and when you want the first subscript to vary fastest.

## Indexing

```matlab
A(2, 3)          % row 2, column 3
A(5)             % linear index, column-major
A(2, :)          % whole row
A(:, 3)          % whole column
A(1:2, 2:3)      % submatrix
A(end, :)        % last row; end works inside any subscript
A(end-2:end, :)  % last three rows
```

### Logical indexing

```matlab
mask = A > 5;            % logical array, same size as A
vals = A(A > 5);         % extract matching elements (column vector)
A(A < 0) = 0;            % conditional assignment
idx = (A > 0) & (A < 10);   % combine with & | ~
```

### Linear vs subscript

```matlab
find(A > 5)                       % linear indices where true
find(A > 5, k, 'last')            % first/last k
[r, c] = find(A > 5);             % subscripts
[r, c] = ind2sub(size(A), lin);   % linear -> subscript
lin = sub2ind(size(A), r, c);     % subscript -> linear
```

## Element-wise vs matrix operators

This distinction is the most frequent source of bugs.

| Element-wise | Matrix |
|---|---|
| `A .* B` | `A * B` (inner-dim must agree) |
| `A ./ B` | `A / B` (solves `X*B = A`) |
| `A .^ n` | `A ^ n` (repeated matmul) |
| `A .'` transpose | `A'` conjugate transpose |

```matlab
C = A + B;   C = A - B;      % element-wise, same shape (or broadcastable)
x = A \ b;                   % solve A*x = b (left division; preferred)
x = b / A;                   % solve x*A = b (right division; b and x are rows)
```

Broadcasting (implicit expansion) applies when one operand is a scalar or a
singleton dimension, e.g. `A - mean(A)` subtracts a row vector from every row.

## Elementwise math

```matlab
abs sqrt exp log log10 log2       % as expected, applied per element
sin cos tan   sind cosd tand      % radians / degrees variants
round floor ceil fix              % rounding (fix truncates toward zero)
real imag conj angle              % complex parts
```

## Concatenation and reshaping

```matlab
[A B]     [A, B]     horzcat(A, B)     cat(2, A, B)   % horizontal
[A; B]    vertcat(A, B)   cat(1, A, B)                % vertical
blkdiag(A, B)                                         % block diagonal

reshape(A, m, n)     % total element count must match; use [] to auto-size one dim
A(:)                 % flatten to column vector (column-major order)
permute(A, [2 1 3])  % generalized transpose for N-D
squeeze(A)           % drop singleton dimensions
repmat(A, m, n)      % tile
repelem(A, m, n)     % repeat each element
fliplr flipud rot90 circshift    % flips / rotations / circular shift
```

## Array information

```matlab
[m, n] = size(A);   size(A, 1)   numel(A)   length(A)   ndims(A)
isempty isscalar isvector isrow iscolumn ismatrix
isnumeric isreal islogical
isnan isinf isfinite            % return logical arrays
isequal(A, B)     isequaln(A, B)   % isequaln treats NaN==NaN
all(A)   any(A)   all(A, dim)   any(A, dim)
```

## Sorting, searching, reduction

```matlab
[B, idx] = sort(A);             % ascending; also returns permutation
sort(A, 'descend')   sort(A, dim)
sortrows(A, col)                % sort rows by column(s)

unique(A)     [B, ia, ic] = unique(A)     unique(A, 'rows')
union intersect setdiff setxor ismember    % set operations

min(A)   max(A)   min(A, [], 'all')        % reductions; 'all' for global
[m, i] = min(A);                           % value and index
mink(A, k)   maxk(A, k)                     % k smallest / largest

sum(A)   sum(A, 'all')   sum(A, dim)   cumsum(A)
prod(A)  cumprod(A)
```

For a global min/max with a linear index, reduce the flattened array:
`[v, i] = max(A(:))`, then `[r, c] = ind2sub(size(A), i)`.
