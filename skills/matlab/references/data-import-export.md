# Data Import and Export

## Text and CSV

Prefer the high-level readers/writers; they infer types and handle headers.

```matlab
T = readtable('data.csv');       % mixed types -> table
M = readmatrix('data.csv');      % numeric matrix
C = readcell('data.csv');        % cell array
S = readlines('data.txt');       % string array, one element per line
str = fileread('data.txt');      % whole file as one char row

writetable(T, 'out.csv');
writematrix(M, 'out.csv', 'Delimiter', '\t');
writecell(C, 'out.csv');
```

Fine control via import options:

```matlab
opts = detectImportOptions('data.csv');
opts.SelectedVariableNames = {'Col1', 'Col3'};
opts.VariableTypes = {'double', 'string', 'double'};
T = readtable('data.csv', opts);
M = readmatrix('data.csv', 'Range', 'B2:D100', 'NumHeaderLines', 1);
```

## Excel

```matlab
T = readtable('data.xlsx', 'Sheet', 'Sheet2');
M = readmatrix('data.xlsx', 'Sheet', 2, 'Range', 'A1:F50');
writetable(T, 'out.xlsx', 'Sheet', 'Results', 'Range', 'B2');
writetable(T2, 'out.xlsx', 'Sheet', 'Data', 'WriteMode', 'append');
```

## MAT files (native)

```matlab
save('d.mat', 'x', 'y');           % specific variables
save('d.mat');                     % entire workspace
save('d.mat', 'big', '-v7.3');     % HDF5 backing, required for >2 GB arrays
save('d.mat', 'x', '-append');

load('d.mat');                     % into current workspace (can clobber names)
S = load('d.mat', 'x', 'y');       % into a struct — safer; then S.x, S.y
who('-file', 'd.mat');             % inspect without loading
```

For arrays too large to hold in memory, use partial access:

```matlab
m = matfile('d.mat');   m.Properties.Writable = true;
chunk = m.big(1:100, :);           % read a slice
m.big(1:100, :) = newData;         % write a slice
```

Note: `-v7.3` MAT files have only partial Octave support; use `-v7` (the default)
for cross-tool exchange.

## Images

```matlab
img = imread('image.png');         % HxWx3 uint8 for RGB
info = imfinfo('image.png');       % Width, Height, ColorType, BitDepth
imwrite(img, 'out.jpg', 'Quality', 95);
imwrite(img, 'out.tiff', 'Compression', 'lzw');
imwrite(X, map, 'indexed.gif');    % indexed image + colormap
```

## Tables

```matlab
T = table(v1, v2, 'VariableNames', {'A', 'B'});
T = array2table(M, 'VariableNames', {'A', 'B', 'C'});
T = struct2table(S);   T = cell2table(C);

col = T.A;             col = T{:, 'A'};        % dot access / brace-to-array
row = T(5, :);         subset = T(T.Value > 5, :);   % logical row filter

T.NewVar = data;   T = removevars(T, 'Old');   T = renamevars(T, 'A', 'Alpha');
T = sortrows(T, 'A', 'descend');
T = innerjoin(T1, T2);   T = outerjoin(T1, T2);
G = groupsummary(T, 'Group', {'mean', 'std'}, 'Value');
```

## Structs and cell arrays

```matlab
S.field = value;   S = struct('a', 1, 'b', 2);
fieldnames(S);   isfield(S, 'a');
S(1).name = 'Alice';  S(2).name = 'Bob';  names = {S.name};   % struct array

C = {1, 'text', [1 2 3]};   x = C{1};   sub = C(1:2);
cell2mat(C)   cell2table(C)   cell2struct(C, fields)
```

## Low-level file I/O

Use only when the high-level readers cannot express the format.

```matlab
fid = fopen('f.txt', 'r');         % modes: r w a, add b for binary (rb/wb)
if fid == -1, error('open failed'); end

data = fscanf(fid, '%f %f', [2 Inf]);   % two columns
C = textscan(fid, '%f %s %f');          % mixed
line = fgetl(fid);                      % one line without newline
fprintf(fid, '%d, %6.2f, %s\n', i, x, s);

raw = fread(fid, Inf, 'uint8');         % binary read
fwrite(fid, data, 'double');            % binary write
fseek(fid, 0, 'bof');   ftell(fid);   feof(fid);
fclose(fid);            % or fclose('all')
```

## Filesystem helpers

```matlab
isfile('f.txt')   isfolder('d')
files = dir('*.csv');   names = {files.name};   % struct array; each has .bytes, .date
fullfile('a', 'b', 'f.txt')                     % OS-correct path join
[p, name, ext] = fileparts('/a/b/f.txt');       % '/a/b', 'f', '.txt'
mkdir('out');   copyfile('a', 'b');   movefile(...);   delete('f.txt');
tempname   tempdir
```
