"""Synthetic ETA model. Not production-validated; risk is a modeling assumption."""
from functools import lru_cache
import json
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from xgboost import XGBRegressor
from app.config import ARTIFACT_DIR, DATA_DIR, SEED

FEATURES = ['base_minutes', 'traffic_severity', 'weather', 'disruption_factor']
MODEL_VERSION = 1


def historical_data(n=6000):
    rng = np.random.default_rng(SEED)
    base = rng.uniform(.5, 240, n)
    traffic, weather, disruption = rng.uniform(0, 1, n), rng.uniform(0, 1, n), rng.uniform(0, 2, n)
    expected = base*(1+.65*traffic+.18*weather+.45*disruption)
    actual = np.maximum(base*.4, expected*(1+rng.normal(0, .10, n)))
    return pd.DataFrame(dict(base_minutes=base, traffic_severity=traffic, weather=weather,
                             disruption_factor=disruption, travel_minutes=actual))


def train(directory: Path = ARTIFACT_DIR / 'risk', history_path: Path = DATA_DIR / 'historical_delay.csv'):
    directory.mkdir(parents=True, exist_ok=True)
    if history_path.exists():
        frame = pd.read_csv(history_path)
    else:
        frame = historical_data()
        history_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(history_path, index=False)
    if len(frame) < 100 or not np.isfinite(frame[FEATURES + ['travel_minutes']].to_numpy()).all():
        raise ValueError('Historical data requires at least 100 finite rows with the documented features.')
    # Independent calibration and test sets: test data never chooses uncertainty.
    train_df, held = train_test_split(frame, test_size=.30, random_state=SEED)
    calibration, test = train_test_split(held, test_size=.5, random_state=SEED)
    model = XGBRegressor(n_estimators=160, max_depth=4, learning_rate=.065,
                         objective='reg:squarederror', random_state=SEED, n_jobs=1)
    model.fit(train_df[FEATURES], train_df.travel_minutes)
    pred_cal = np.maximum(1, model.predict(calibration[FEATURES]))
    relative_error = (calibration.travel_minutes.to_numpy()-pred_cal)/pred_cal
    relative_sd = max(.10, float(np.sqrt(np.mean(relative_error**2))))
    pred_test = np.maximum(1, model.predict(test[FEATURES]))
    metadata = dict(version=MODEL_VERSION, seed=SEED, features=FEATURES, train_rows=len(train_df),
                    calibration_rows=len(calibration), test_rows=len(test),
                    relative_sd=relative_sd, test_mae_minutes=float(mean_absolute_error(test.travel_minutes, pred_test)),
                    test_90pct_coverage=float(np.mean(np.abs(test.travel_minutes-pred_test) <= 1.645*relative_sd*pred_test)),
                    disclaimer='This prediction model is trained on synthetic demonstration data and is not production-validated.')
    model.save_model(directory / 'eta.ubj')
    (directory / 'metadata.json').write_text(json.dumps(metadata, indent=2))
    return model, metadata


@lru_cache(maxsize=1)
def load_model():
    directory = ARTIFACT_DIR / 'risk'
    if (directory / 'eta.ubj').exists() and (directory / 'metadata.json').exists():
        try:
            metadata = json.loads((directory / 'metadata.json').read_text())
            if metadata['version'] != MODEL_VERSION or metadata['features'] != FEATURES or metadata['relative_sd'] <= 0:
                raise ValueError('Incompatible model metadata')
            model = XGBRegressor()
            model.load_model(directory / 'eta.ubj')
            return model, metadata
        except Exception as exc:
            warnings.warn(f'Local model could not be loaded; retraining once ({type(exc).__name__}).')
    return train()


def predict_matrix(matrix, conditions):
    model, metadata = load_model()
    base = matrix.minutes.ravel()
    frame = pd.DataFrame({'base_minutes': base, 'traffic_severity': conditions.traffic_severity,
                          'weather': conditions.weather, 'disruption_factor': conditions.disruption_factor})
    prediction = np.maximum(base*.5, model.predict(frame)).reshape(matrix.minutes.shape)
    prediction[matrix.minutes == 0] = 0
    sd = prediction*metadata['relative_sd']
    return prediction, sd


if __name__ == '__main__':
    _, result = train()
    print(json.dumps(result, indent=2))
