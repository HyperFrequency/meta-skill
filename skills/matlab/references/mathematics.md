# Mathematics

## Linear algebra

### Solving systems

```matlab
x = A \ b;            % solve A*x = b — the default; picks a solver from A's shape
x = b / A;            % solve x*A = b (right division)
x = linsolve(A, b, opts);   % when you can assert structure (see below)
```

Avoid `inv(A)*b`: it is slower and less accurate than `A\b`. Reserve `inv` for
when you genuinely need the inverse matrix itself.

`linsolve` structure hints (skip factorization work when you know the shape):

```matlab
opts.LT = true;      % lower triangular
opts.UT = true;      % upper triangular
opts.SYM = true;     % symmetric
opts.POSDEF = true;  % symmetric positive definite
```

Over/under-determined systems: `A\b` returns a least-squares (or minimum-norm)
solution; `lsqminnorm(A,b)` forces minimum norm; `lsqnonneg(A,b)` enforces `x>=0`.

### Decompositions

```matlab
[L, U, P] = lu(A);        % P*A = L*U
[Q, R] = qr(A);           % A = Q*R ; qr(A,0) for economy size
R = chol(A);              % A = R'*R, requires symmetric positive definite
[L, D] = ldl(A);          % symmetric indefinite
[U, T] = schur(A);        % A = U*T*U'
[U, S, V] = svd(A);       % A = U*S*V' ; svd(A,'econ') for economy size
```

### Eigenvalues and SVD subsets

```matlab
e = eig(A);               [V, D] = eig(A);      % A*V = V*D
e = eig(A, B);            % generalized: A*v = lambda*B*v
e = eigs(A, k);           % k eigenvalues of a large/sparse matrix
[U, S, V] = svds(A, k);   % k largest singular values
```

### Properties

```matlab
det(A)   trace(A)   rank(A)
norm(A)          % 2-norm (largest singular value) by default
norm(A, 1)   norm(A, inf)   norm(A, 'fro')
cond(A)          % condition number (largest/smallest singular value)
rcond(A)         % fast reciprocal-condition estimate
pinv(A)          % Moore-Penrose pseudoinverse (via SVD)
```

## Elementary functions

Trig (`sin`/`cos`/`tan`, degree variants `sind`/…, inverses, `atan2`,
hyperbolic `sinh`/…), exponentials/logs (`exp`, `log`, `log10`, `log2`,
`log1p` for accuracy near zero, `nthroot`), complex handling (`complex`,
`real`, `imag`, `abs`, `angle`, `conj`, `cart2pol`/`pol2cart`), rounding
(`round`, `floor`, `ceil`, `fix`, `mod` vs `rem`, `sign`), and special
functions (`gamma`, `gammaln`, `factorial`, `nchoosek`, `erf`/`erfc`,
`besselj`/`bessely`/`besseli`/`besselk`, `legendre`).

## Calculus

```matlab
% Numerical integration of a function handle
integral(@(x) x.^2, 0, 1)
integral(fun, 0, Inf)                  % improper / infinite limits allowed
integral2(fun, xa, xb, ya, yb)         % double; integral3 for triple
integral(fun, a, b, 'RelTol', 1e-8)

% Integration of sampled data
trapz(x, y)     cumtrapz(x, y)

% Differentiation
diff(y)   diff(y, n)                   % n-th finite differences
gradient(y, h)                         % central-difference derivative
[gx, gy] = gradient(Z, hx, hy);        % 2-D gradient
```

## Differential equations

```matlab
odefun = @(t, y) -2*y;                 % dy/dt = f(t, y)
[t, y] = ode45(odefun, [0 5], y0);     % tspan, initial condition
```

Solver selection:

| Solver | Use when |
|---|---|
| `ode45` | non-stiff, medium accuracy — the default first try |
| `ode23` | non-stiff, low accuracy, crude tolerances |
| `ode113` | non-stiff, stringent tolerances, expensive `f` |
| `ode15s` | stiff, or `ode45` is crawling / taking tiny steps |
| `ode23s`, `ode23t`, `ode23tb` | stiff, low order / specific methods |

Higher-order ODEs become first-order systems. For `y'' + 2y' + y = 0` set
`y1 = y`, `y2 = y'`:

```matlab
odefun = @(t, y) [y(2); -2*y(2) - y(1)];
[t, y] = ode45(odefun, [0 10], [1; 0]);   % y(:,1) is the solution
```

Tune with `odeset('RelTol', 1e-6, 'AbsTol', 1e-9, 'Events', @ev)`. Boundary-value
problems use `bvp4c` with an `odefun`, a boundary-residual `bcfun`, and a
`bvpinit` guess.

## Optimization and roots

```matlab
[x, fval] = fminbnd(fun, x1, x2);      % scalar, bounded
[x, fval] = fminsearch(fun, x0);       % multivariable, derivative-free (simplex)
x = fzero(fun, x0);                    % root near x0, or fzero(fun, [a b]) to bracket
r = roots([1 0 -4]);                   % polynomial roots ([2; -2])
x = lsqnonlin(fun, x0);                % minimize sum(fun(x).^2)
x = lsqcurvefit(model, p0, xdata, ydata);   % nonlinear curve fit
```

Pass `optimset('Display','iter','TolX',1e-8,'TolFun',1e-8)` to watch progress.
`fmincon`/`fminunc`/`ga` require the Optimization / Global Optimization Toolboxes.

## Statistics

```matlab
mean median mode std var range iqr        % add 'omitnan' to skip NaN
geomean harmmean
corrcoef(X, Y)   cov(X, Y)                % correlation / covariance
prctile(x, [25 50 75])   quantile(x, [.25 .5 .75])
movmean(x, k)   movmedian movstd movsum   % windowed statistics
[N, edges] = histcounts(x, 'Normalization', 'pdf');
```

## Signal processing

```matlab
Y = fft(x);            Y = fft(x, n);          % n-point (zero-pad/truncate)
x = ifft(Y);           Y2 = fft2(X);
Ys = fftshift(Y);                              % zero frequency to center
f  = (0:n-1) * fs / n;                         % frequency axis, fs = sample rate

y = filter(b, a, x);        y = filtfilt(b, a, x);   % filtfilt is zero-phase
y = conv(x, h, 'same');     Y = conv2(X, H, 'same'); % convolution
[r, lags] = xcorr(x, y, 'coeff');                    % normalized cross-corr
```

`fir1`, `butter`, `freqz`, etc. require the Signal Processing Toolbox (MATLAB)
or `pkg load signal` (Octave).

## Interpolation and fitting

```matlab
interp1(x, y, xi, 'spline')     % 'linear' default; also 'pchip', 'nearest'
interp2(X, Y, Z, xi, yi)        interp3(...)
F = scatteredInterpolant(x, y, v);   vi = F(xi, yi);   % scattered data

p = polyfit(x, y, n);   yi = polyval(p, xi);           % least-squares poly fit
[p, S] = polyfit(x, y, n);  [yi, delta] = polyval(p, xi, S);   % error estimate
polyder(p)   polyint(p)   roots(p)   poly(r)           % polynomial calculus
```

Linearizable fits: for `y = a*exp(b*x)`, fit `polyfit(x, log(y), 1)` then
`b = p(1)`, `a = exp(p(2))`. For `y = a*x^b`, fit `polyfit(log(x), log(y), 1)`.
For genuinely nonlinear models use `lsqcurvefit` with an initial guess.
