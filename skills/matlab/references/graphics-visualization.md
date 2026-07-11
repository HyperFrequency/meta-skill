# Graphics and Visualization

## 2D plots

```matlab
plot(x, y)                 plot(x, y, 'r--o')
plot(x1, y1, x2, y2)       % multiple series in one call
plot(x, y, 'LineWidth', 2, 'Color', [0.2 0.4 0.8])
h = plot(x, y);  h.LineWidth = 2;   % keep the handle to edit later
```

Line spec is `[color][marker][linestyle]`:

- Colors: `r g b c m y k w`
- Markers: `o + * . x s d ^ v > < p h`
- Line styles: `-` solid, `--` dashed, `:` dotted, `-.` dash-dot

Other 2D families: `scatter(x,y,sz,c,'filled')`, `bar`/`barh` (add `'stacked'`),
`area`, `histogram(x, nbins)` (with `'Normalization','pdf'`), `errorbar(x,y,err)`,
log-axis `semilogx`/`semilogy`/`loglog`, and `polarplot(theta, rho)`.

## 3D plots

```matlab
[X, Y] = meshgrid(-2:0.1:2, -2:0.1:2);
Z = X.^2 + Y.^2;
surf(X, Y, Z, 'EdgeColor', 'none', 'FaceColor', 'interp');
mesh(X, Y, Z);                 % wireframe
contour(X, Y, Z, levels);      contourf(...)    % 2D contours; contour3 for 3D
imagesc(data);  colorbar;      % scaled color image (heat-map style)
plot3(x, y, z)   scatter3(x, y, z, sz, c, 'filled')
quiver(X, Y, U, V)             % vector field; quiver3 for 3D
```

View and shading: `view(az, el)` / `view(2)` / `view(3)`; `shading interp`;
`lighting gouraud` with `light('Position', [...])`; `material shiny`.

## Specialized plots

`boxplot(data, groups)`, `heatmap(xLabels, yLabels, data)`, `imshow(img)` /
`imshow(img, [])` for image display, `pie(X, labels)`, `stem`/`stairs`,
`streamline` for flow fields.

## Composing figures

```matlab
figure('Name', 'Results', 'Position', [100 100 800 600]);

subplot(2, 2, 1);   plot(...)      % classic grid, position p in an m-by-n grid
subplot(2, 2, [1 2]);              % span cells

tiledlayout(2, 2);                 % modern layout with tighter spacing
nexttile;  plot(...)
nexttile([1 2]);                   % span two columns

hold on;  plot(x, y1);  plot(x, y2);  hold off;   % overlay on one axes

yyaxis left;  plot(x, y1);  yyaxis right;  plot(x, y2);   % dual y-axes
linkaxes([ax1, ax2], 'x');         % share limits across axes
```

`gcf` / `gca` return the current figure / axes handles.

## Customization

```matlab
title('T', 'FontSize', 14, 'FontWeight', 'bold');
xlabel('Time (s)');   ylabel('y');   zlabel('z');
title('$\int_0^1 x^2\,dx$', 'Interpreter', 'latex');   % LaTeX math

legend({'a', 'b'}, 'Location', 'best');   % or 'northeastoutside'
axis([xmin xmax ymin ymax]);   xlim(...)   ylim(...)
axis equal | square | tight | off;
grid on;   grid minor;   box on;
xticks(0:5);   xticklabels({'A','B',...});   xtickangle(45);
set(gca, 'YDir', 'reverse');

colormap(parula)   % default; also jet hot cool gray turbo viridis
colorbar;   clim([cmin cmax]);      % clim replaces the older caxis (R2022a+)
colororder(colors);                 % default line color cycle (R2019b+)

text(x, y, 'peak', 'Color', 'red');
xline(5, '--r', 'threshold');   yline(10);
annotation('textarrow', [x1 x2], [y1 y2], 'String', 'note');
```

## Export

Prefer `exportgraphics` (R2020a+) — it crops tightly and honors resolution:

```matlab
exportgraphics(gcf, 'fig.png', 'Resolution', 300);
exportgraphics(gcf, 'fig.pdf', 'ContentType', 'vector');   % true vector PDF
exportgraphics(gca, 'axes_only.png');
copygraphics(gcf, 'ContentType', 'vector');                % to clipboard
```

Older / more explicit control:

```matlab
saveas(gcf, 'fig.png');        saveas(gcf, 'fig.fig');   % .fig is MATLAB-native
print('-dpng', '-r300', 'fig.png');
print('-dpdf', '-painters', 'fig.pdf');   % -painters forces vector output
print('-depsc', 'fig.eps');               % color EPS for LaTeX
```

For headless runs, create figures without a display and export directly — no
`figure` window is needed under `matlab -batch` or `octave --no-gui`.
