# Parameters

`params = Simul.create_default_params()` returns a hierarchical object. Set
values with dot notation; unknown attributes raise `AttributeError`, which
catches typos immediately.

```python
params.group.subgroup.parameter = value
```

## Operators — `params.oper`

Domain size and resolution.

```python
params.oper.nx = 256          # grid points, x
params.oper.ny = 256          # grid points, y
params.oper.nz = 128          # z (3D solvers only)

params.oper.Lx = 2 * pi       # box length, x
params.oper.Ly = 2 * pi
params.oper.Lz = pi           # 3D only

params.oper.coef_dealiasing = 2. / 3.   # dealiasing cutoff (default 2/3)
```

Use powers of two (128, 256, 512, 1024) for fast FFTs. The 2/3 dealiasing rule
means the largest reliably resolved wavenumber is `(2/3) * n/2`, so effective
resolution is below the raw grid count.

## Viscosity and dissipation

```python
params.nu_2 = 1e-3    # Laplacian (Newtonian) viscosity
params.nu_4 = 0       # hyperviscosity (4th order)
params.nu_8 = 0       # hyper-hyperviscosity (8th order)
```

Higher-order terms damp only the smallest scales, keeping large-scale dynamics
intact — useful to stabilize under-resolved high-Reynolds runs.

## Stratification / rotation (solver-specific)

```python
params.N  = 1.0    # Brunt-Vaisala frequency (stratified solvers)
params.f  = 1.0    # Coriolis parameter (sw1l)
params.c2 = 10.0   # squared gravity-wave phase speed (sw1l)
```

## Time stepping — `params.time_stepping`

```python
params.time_stepping.t_end = 10.0           # stop time
params.time_stepping.it_end = 100           # or stop by iteration count
params.time_stepping.deltat0 = 0.01         # initial dt
params.time_stepping.USE_CFL = True         # adaptive dt from a CFL condition
params.time_stepping.CFL = 0.5              # CFL number when USE_CFL
params.time_stepping.type_time_scheme = "RK4"   # e.g. "RK4", "RK2"
```

Recommended default: `USE_CFL = True` with `CFL = 0.5`. Confirm the exact set of
supported time-scheme names against your installed version.

## Initial fields — `params.init_fields`

```python
params.init_fields.type = "noise"   # noise | dipole | vortex | from_file | in_script
```

From a saved file:

```python
params.init_fields.type = "from_file"
params.init_fields.from_file.path = "path/to/state_phys_t5.000.h5"
```

In-script (full control): set `type = "in_script"`, instantiate, write the
**physical** state arrays, then sync the spectral state the solver integrates:

```python
params.init_fields.type = "in_script"
sim = Simul(params)

X, Y = sim.oper.get_XY_loc()
# names are solver-specific — check sim.state.keys_state_phys
vx = sim.state.state_phys.get_var("vx")
vy = sim.state.state_phys.get_var("vy")
vx[:] = np.sin(X) * np.cos(Y)
vy[:] = -np.cos(X) * np.sin(Y)

sim.state.statespect_from_statephys()   # phys -> spect, required
sim.time_stepping.start()
```

`statespect_from_statephys()` recomputes the spectral fields from the physical
fields you just set. Skipping it means the solver integrates the (empty/stale)
spectral state and your IC is ignored.

## Output — `params.output`

```python
params.output.sub_directory = "my_run"          # folder under FLUIDSIM_PATH

# save periods (in simulation time units; 0 disables that output)
params.output.periods_save.phys_fields = 1.0
params.output.periods_save.spectra = 0.5
params.output.periods_save.spatial_means = 0.1
params.output.periods_save.spect_energy_budg = 0.5

# console status cadence
params.output.periods_print.print_stdout = 0.5

# live plotting (optional)
params.output.ONLINE_PLOT_OK = True
params.output.periods_plot.phys_fields = 2.0
```

## Forcing — `params.forcing`

```python
params.forcing.enable = True
params.forcing.type = "tcrandom"     # tcrandom | proportional | in_script
params.forcing.nkmin_forcing = 2     # forced wavenumber band (min)
params.forcing.nkmax_forcing = 5     # forced wavenumber band (max)
params.forcing.forcing_rate = 1.0    # energy injection rate
```

## Inspecting and saving parameters

```python
params._print_as_xml()               # dump every parameter
params._save_as_xml("params.xml")    # persist configuration
```

Parameters are also written automatically alongside simulation output
(`params_simul.xml`).
