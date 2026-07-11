# Python Integration

Two directions: call Python from MATLAB (the `py.` bridge) or call MATLAB from
Python (the MATLAB Engine API).

## Python from MATLAB

### Configure the interpreter

```matlab
pyenv                                   % show current config
pyenv('Version', '/usr/bin/python3');   % set BEFORE any Python call
pe = pyenv;  disp(pe.Executable);
```

### Call functions and import modules

```matlab
py.len([1 2 3])          py.math.sqrt(16)      % builtins / stdlib via py.
np = py.importlib.import_module('numpy');
arr = np.array({1, 2, 3, 4, 5});
m = np.mean(arr);
arr2 = py.numpy.array({1, 2, 3});             % direct py. syntax also works
```

### Keyword arguments and running code

```matlab
py.sorted({3, 1, 2}, pyargs('reverse', true));     % pyargs wraps kwargs

pyrun("y = x * 2", "y", x=5);          % run a statement, return a variable
pyrunfile("script.py", "out");         % run a file, return a variable
```

### Type conversion

| MATLAB | Python |
|---|---|
| `double`, `single` | `float` |
| `int*`/`uint*` | `int` |
| `logical` | `bool` |
| `char`, `string` | `str` |
| cell array | `list` |
| struct | `dict` |
| numeric array | `numpy.ndarray` (if NumPy present) |

Convert Python results back explicitly:

```matlab
double(py.float(3.14))     char(py.str('hi'))     cell(py.list({1,2,3}))
double(py.numpy.array({1,2,3}))
```

NumPy is row-major (C order); MATLAB is column-major (Fortran order). Transpose
or reshape when the layout matters after a round trip.

### Work with Python objects

```matlab
L = py.list({3, 1, 2});   L.append(9);   L.sort();
methods(L)        % list methods on a Python object
items = cell(L);  for i = 1:numel(items); disp(items{i}); end   % iterate
```

### Error handling

```matlab
try
    r = py.some_module.might_fail();
catch ME
    if isa(ME, 'matlab.exception.PyException')
        disp(ME.message);
    else
        rethrow(ME);
    end
end
```

## MATLAB from Python

### Start the engine

```python
import matlab.engine
eng = matlab.engine.start_matlab()        # fresh session
# eng = matlab.engine.connect_matlab()    # attach to a shared session
```

The MATLAB Engine API for Python must be installed from a MATLAB install
(`cd(fullfile(matlabroot,'extern','engines','python'))`, then
`python setup.py install`) or via `pip install matlabengine` matched to your
MATLAB release.

### Call functions

```python
eng.sqrt(16.0)
mean_val, std_val = eng.std([1.0, 2, 3, 4, 5], nargout=2)   # multiple returns
A = matlab.double([[1, 2], [3, 4]])
B = eng.inv(A)
eng.myfunction(arg1, arg2)            # any function on the MATLAB path
eng.quit()
```

### Pass data

```python
matlab.double([1.0, 2.0, 3.0])           # 1-D
matlab.double([[1, 2], [3, 4]])          # 2-D
matlab.int32([1, 2, 3])
matlab.double([1+2j], is_complex=True)
# From NumPy: matlab.double(np_array.tolist())
```

### Async calls

```python
future = eng.sqrt(16.0, background=True)
...                                       # do other work
if future.done():
    result = future.result()
```

## Sharing data via files

Often simpler than a live bridge:

```matlab
save('shared.mat', 'data', 'labels');    % MATLAB writes
```

```python
import scipy.io
m = scipy.io.loadmat('shared.mat')       # Python reads
scipy.io.savemat('back.mat', {'result': arr})
```

Or exchange CSV with `writematrix`/`readmatrix` on the MATLAB side and
`pandas`/`numpy` on the Python side.
