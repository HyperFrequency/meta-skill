# Programming

## Scripts vs functions

- A **script** is a `.m` file of commands that runs in the base workspace and
  shares variables with it.
- A **function** has its own workspace and must live in a file named after the
  function (or be a local function after the main one).

```matlab
function y = myfunction(x)
%MYFUNCTION Brief one-line summary shown by `help myfunction`.
%   Y = MYFUNCTION(X) returns X squared, element-wise.
    y = x.^2;
end

function [a, b] = twoOutputs(x)   % multiple returns
    a = x.^2;   b = x.^3;
end

function varargout = flexible(varargin)   % variable arity
    n = nargin;   m = nargout;            % counts
end
```

Local functions follow the main function in the same file and are visible only
within it.

## Input validation

`arguments` blocks (R2019b+) declare size, type, defaults, and validators:

```matlab
function result = scaleData(x, options)
    arguments
        x (1,:) double {mustBePositive}
        options.Normalize (1,1) logical = false
        options.Scale (1,1) double {mustBePositive} = 1
    end
    result = x * options.Scale;
    if options.Normalize
        result = result / max(result);
    end
end

y = scaleData([1 2 3], 'Normalize', true, 'Scale', 2);
```

Common validators: `mustBePositive`, `mustBeNonnegative`, `mustBeInteger`,
`mustBeFinite`, `mustBeReal`, `mustBeNonempty`, `mustBeMember`, `mustBeInRange`.

## Control flow

```matlab
if a > 0 && b > 0        % && / || short-circuit on scalars
    ...
elseif a < 0
    ...
else
    ...
end

switch key
    case {'sat', 'sun'};  kind = 'weekend';
    otherwise;            kind = 'weekday';
end

for i = 1:n; ...; end     % also `for col = A` iterates columns
while cond; ...; end
break;   continue;   return;
```

Use `&`/`|` for element-wise logical arrays and `&&`/`||` for scalar
short-circuit conditions.

## Function types

```matlab
f = @(x) x.^2 + 1;             % anonymous; captures workspace values by copy
a = 2;  h = @(x) a*x;          % h freezes a=2 even if a changes later

g = @sin;   name = func2str(g);   g2 = str2func('cos');   % handles
result = integral(f, 0, 1);    % pass handles to higher-order functions
```

Nested functions (defined inside another function) share the parent's workspace;
anonymous functions only capture a snapshot.

## Error handling

```matlab
try
    result = risky();
catch ME
    fprintf('%s: %s\n', ME.identifier, ME.message);
    rethrow(ME);            % or handle and continue
end

% Dispatch on identifier
switch ME.identifier
    case 'MATLAB:nomem';  rethrow(ME);
    otherwise;            result = NaN;
end

error('MyPkg:BadInput', 'value %f out of range', v);
assert(x > 0, 'MyPkg:NotPositive', 'x must be positive');
warning('MyPkg:Deprecated', 'use foo instead');
warning('off', 'MATLAB:nearlySingularMatrix');   % suppress a specific warning
```

`getReport(ME)` yields a full formatted stack trace — useful before `exit(1)` in
batch runs.

## Performance

Two rules dominate:

```matlab
% 1. Vectorize — let built-ins operate on whole arrays
y = sin(x);        s = sum(x);       y = x(x > 0);   % not a find + index loop

% 2. Preallocate any loop you cannot vectorize
y = zeros(1, n);                     % NOT y = []
for i = 1:n
    y(i) = compute(i);
end
```

Measure before optimizing:

```matlab
tic;  ...;  toc;                     % wall clock
profile on;  myfunction();  profile viewer;   profile off;   % line profiler
```

Embarrassingly parallel loops (Parallel Computing Toolbox):

```matlab
parfor i = 1:n                       % iterations must be independent
    results(i) = compute(i);
end
parpool(4);   delete(gcp('nocreate'));
```

## Debugging

```matlab
dbstop in myfun at 10        dbstop if error       dbstop if naninf
dbstep   dbstep in   dbcont   dbquit
dbstack                      % call stack
whos                         % variables and sizes
clearvars -except x y        % selective clear
```

## Object-oriented programming

```matlab
classdef MyClass
    properties
        Value
    end
    properties (Constant)
        Answer = 42
    end
    methods
        function obj = MyClass(v)     % constructor
            obj.Value = v;
        end
        function r = scale(obj, x)
            r = obj.Value * x;
        end
    end
    methods (Static)
        function r = square(x); r = x.^2; end
    end
end
```

Value vs handle semantics — the key distinction:

```matlab
% Value class (default): assignment copies
a = MyClass(1);  b = a;  b.Value = 2;   % a.Value still 1

% Handle class: assignment aliases the same object
classdef Node < handle
    properties;  Data;  end
end
a = Node();  a.Data = 1;  b = a;  b.Data = 2;   % a.Data is now 2
```

Inheritance uses `classdef Derived < Base`, calls the superclass constructor with
`obj@Base(...)`, and invokes overridden parent methods with `method@Base(obj,...)`.
Handle classes can declare `events` and register `addlistener` callbacks.
