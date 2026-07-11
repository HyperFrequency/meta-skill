# Data Handling and Preprocessing

## The survival outcome

sksurv represents `y` as a NumPy **structured array** with two fields:

- `event` — boolean; `True` = event observed, `False` = right-censored.
- `time` — float; observed event or censoring time (must be positive, finite).

```python
import numpy as np
from sksurv.util import Surv

event = np.array([True, False, True, False, True])
time  = np.array([5.2, 10.1, 3.7, 8.9, 6.3])
y = Surv.from_arrays(event=event, time=time)
print(y.dtype)   # [('event', '?'), ('time', '<f8')]
```

sksurv is built for **right censoring** (subject event-free at last follow-up,
lost to follow-up, or withdrawn). Left- and interval-censoring need other tools.

## Loading data

### Built-in datasets

```python
from sksurv.datasets import (
    load_aids, load_breast_cancer, load_flchain, load_gbsg2,
    load_veterans_lung_cancer, load_whas500, load_bmt, load_cgvhd,
)

X, y = load_breast_cancer()   # X: DataFrame of features, y: structured array
print(X.shape, y["event"].sum(), f"{1 - y['event'].mean():.1%} censored")
```

`load_bmt` and `load_cgvhd` carry multiple event types for competing-risks work.
`load_arff_files_standardized` and `get_x_y` load and split custom ARFF data.

### From a DataFrame or CSV

```python
import pandas as pd
from sksurv.util import Surv

df = pd.read_csv("survival_data.csv")
X  = df.drop(columns=["time", "event"])
y  = Surv.from_dataframe("event", "time", df)
# equivalently:
y  = Surv.from_arrays(event=df["event"].astype(bool), time=df["time"].astype(float))
```

### From ARFF

```python
from sksurv.io import loadarff
X, y = loadarff("survival_data.arff")
```

## Preprocessing

### Categorical encoding

```python
from sksurv.preprocessing import OneHotEncoder, encode_categorical

X_enc = OneHotEncoder().fit_transform(X[categorical_cols])  # explicit columns
X_enc = encode_categorical(X)                               # auto-encode all categoricals
# or plain pandas: pd.get_dummies(X, drop_first=True)
```

### Standardization

Required for SVMs and penalized Cox; harmless for tree ensembles.

```python
from sklearn.preprocessing import StandardScaler
X_scaled = StandardScaler().fit_transform(X)   # fit on train, transform on test
```

Prefer fitting the scaler inside a `Pipeline` so it never sees test rows.

### Missing values

```python
from sklearn.impute import SimpleImputer
X_num = SimpleImputer(strategy="mean").fit_transform(X.select_dtypes("number"))
X_cat = SimpleImputer(strategy="most_frequent").fit_transform(X.select_dtypes("object"))
# For MICE-style imputation:
from sklearn.experimental import enable_iterative_imputer   # noqa: F401
from sklearn.impute import IterativeImputer
X_imp = IterativeImputer(random_state=42).fit_transform(X)
```

Never impute the outcome. Drop rows with missing/invalid `time` before modeling.

## Data-quality checks

Run these before fitting — they catch the errors that silently break survival models.

```python
import numpy as np

def validate_survival_data(y):
    if np.any(y["time"] <= 0):
        print("WARNING: non-positive survival times:", int(np.sum(y["time"] <= 0)))
    if np.any(~np.isfinite(y["time"])):
        print("WARNING: non-finite survival times:", int(np.sum(~np.isfinite(y["time"]))))
    censor_rate = 1 - y["event"].mean()
    print(f"Censoring rate: {censor_rate:.1%}  |  events: {int(y['event'].sum())}")
    if censor_rate > 0.4:
        print("  -> prefer Uno's C-index (concordance_index_ipcw) over Harrell's")

def events_per_feature(X, y, minimum=10):
    ratio = y["event"].sum() / X.shape[1]
    print(f"Events per feature: {ratio:.1f}")
    if ratio < minimum:
        print("  -> regularize (Coxnet), select features, or collect more data")
    return ratio
```

Rule of thumb: **~10+ events per feature** for a stable Cox model.

## Train/test split with balanced censoring

A random split can leave lopsided censoring rates. Stratify on event status and
time quartiles:

```python
import pandas as pd
from sklearn.model_selection import train_test_split

strat = y["event"].astype(int) * 10 + pd.qcut(y["time"], q=4, labels=False)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=strat, random_state=42
)
```

Verify the two splits have similar censoring rate and median time afterward.

## Time-varying covariates

sksurv fixes covariates at baseline and does **not** support time-varying
covariates. For those, use `lifelines` (time-varying Cox), landmarking, or a
counting-process reformulation.

## End-to-end template

```python
from sksurv.util import Surv
from sksurv.preprocessing import encode_categorical
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import pandas as pd

df = pd.read_csv("data.csv")
y  = Surv.from_dataframe("event", "time", df)
X  = df.drop(columns=["event", "time"])

validate_survival_data(y); events_per_feature(X, y)

X = encode_categorical(X.fillna(X.median(numeric_only=True)))
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler().fit(X_train)   # fit on train only
X_train_scaled, X_test_scaled = scaler.transform(X_train), scaler.transform(X_test)
```
