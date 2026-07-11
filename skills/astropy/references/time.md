# Time (`astropy.time`)

`Time` represents instants with sub-nanosecond precision (stored as two 64-bit
floats) and knows both its **format** (how the number is written) and its
**scale** (which physical time standard it is on).

## Creating

```python
from astropy.time import Time
import astropy.units as u

Time("2023-01-15 12:30:45")                 # ISO, auto-detected, UTC by default
Time("2023-01-15 12:30:45", format="iso", scale="utc")
Time(2460000.0, format="jd")                # Julian Date
Time(59945.0, format="mjd")                 # Modified Julian Date
Time(1673785845.0, format="unix")           # Unix seconds
Time(["2023-01-01", "2023-06-01"])          # array of times
```

## Formats

`iso`, `isot`, `jd`, `mjd`, `decimalyear`, `jyear`, `byear`, `yday`
(`"2023:046"`), `fits`, `gps`, `unix`, `plot_date`, plus Python `datetime`
objects. Read a time back in any format via the matching attribute:

```python
t = Time("2023-01-15 12:30:45")
t.jd, t.mjd, t.iso, t.isot, t.unix, t.decimalyear
t.format = "mjd"        # change the default display format
```

For maximum precision use `to_value` with a subformat:

```python
t.to_value("mjd", subfmt="decimal")   # highest precision
t.to_value("mjd", subfmt="long")      # extended float
```

## Scales

`utc` (default), `tai` (atomic), `tt` (terrestrial), `tdb` (barycentric
dynamical), `tcg`, `tcb`, `ut1`. Convert by attribute:

```python
t = Time("2023-01-15 12:00:00", scale="utc")
t.tai, t.tt, t.tdb, t.ut1
(t.tai - t.utc).sec        # 37 s (accumulated leap seconds)
```

`ut1` and sidereal time need the IERS Earth-orientation table, downloaded and
cached on first use (network required initially).

## Arithmetic

Subtracting two `Time`s gives a `TimeDelta`; add a `TimeDelta` or a `Quantity`
of time to shift:

```python
from astropy.time import TimeDelta

dt = Time("2023-02-15") - Time("2023-01-15")   # TimeDelta
dt.jd, dt.sec, dt.to(u.day)

t = Time("2023-01-15 12:00:00")
t + TimeDelta(7, format="jd")     # +7 days
t + 1*u.hour                      # add a Quantity
t - 1*u.week

start = Time("2023-01-01")
start + np.arange(365)*u.day      # regular daily series
```

## Observing features

Sidereal time and barycentric/heliocentric light-travel corrections need a
`location` (and, for corrections, a target `SkyCoord`):

```python
from astropy.coordinates import EarthLocation, SkyCoord

loc = EarthLocation(lat=40*u.deg, lon=-120*u.deg, height=1000*u.m)
t = Time("2023-06-15 23:00:00", location=loc)
t.sidereal_time("apparent")       # local apparent sidereal time
t.sidereal_time("mean")

target = SkyCoord(ra=10*u.deg, dec=20*u.deg)
times = Time(["2023-01-01", "2023-06-01"], location=loc)
ltt = times.light_travel_time(target, kind="barycentric")   # or "heliocentric"
times_bary = times.tdb + ltt      # barycentric times
```

`Time.earth_rotation_angle(longitude)` returns the Earth rotation angle for
celestial-to-terrestrial work.

## Missing values

```python
times = Time(["2023-01-01", "2023-06-01", "2023-12-31"])
times[1] = np.ma.masked
times.mask                # [False True False]
times.filled(Time("2000-01-01"))
```

## Formatting and time zones

```python
t.strftime("%Y-%m-%d %H:%M:%S")
dt = t.to_datetime()      # aware conversion; combine with pytz/zoneinfo for TZ
```

## Performance

- Vectorize: process arrays of times, not one-at-a-time loops.
- Format conversions are cached, so repeated access is cheap.
- Precision is maintained across century-scale spans thanks to the two-float
  internal representation.
