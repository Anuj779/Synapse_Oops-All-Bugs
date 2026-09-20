"""Optional Valhalla matrix with bounded timeout, verified cache, offline fallback."""
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import warnings
import numpy as np
import httpx
from app.config import ARTIFACT_DIR
from models.schemas import Scenario


@dataclass
class Matrix:
    distance: np.ndarray
    minutes: np.ndarray
    mode: str


def locations(s: Scenario):
    return [t.current_location for t in s.trucks] + [o.location for o in s.orders]


def fallback(s: Scenario) -> Matrix:
    points = locations(s)
    distance = np.zeros((len(points), len(points)))
    for i, a in enumerate(points):
        for j, b in enumerate(points):
            lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
            dlat, dlon = lat2-lat1, math.radians(b.lon-a.lon)
            h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
            distance[i, j] = 6371 * 2 * math.asin(min(1, math.sqrt(h))) * 1.25
    return Matrix(distance, distance / 55 * 60, 'Demo Fallback')


def get_matrix(s: Scenario, endpoint: str | None = None, cache_dir: Path = ARTIFACT_DIR / 'routing') -> Matrix:
    endpoint = endpoint if endpoint is not None else os.getenv('VALHALLA_URL', '')
    coords = [p.model_dump() for p in locations(s)]
    key = hashlib.sha256(json.dumps([coords, endpoint, 'truck-v1'], sort_keys=True).encode()).hexdigest()
    path = cache_dir / f'{key}.json'
    def parse(payload, mode):
        d, t = np.array(payload['distance'], dtype=float), np.array(payload['minutes'], dtype=float)
        n = len(coords)
        if d.shape != (n, n) or t.shape != (n, n) or not np.isfinite(d).all() or not np.isfinite(t).all() or (d < 0).any() or (t < 0).any():
            raise ValueError('Invalid routing matrix')
        for i in range(n):
            for j in range(n):
                if coords[i] != coords[j] and (d[i, j] <= 0 or t[i, j] <= 0):
                    raise ValueError('Unreachable or invalid routing pair')
        return Matrix(d, t, mode)
    if path.exists():
        try:
            return parse(json.loads(path.read_text()), 'Valhalla (cached)')
        except (ValueError, KeyError, TypeError, OSError):
            warnings.warn('Routing cache invalid; using provider or fallback.')
    if endpoint:
        try:
            response = httpx.post(endpoint.rstrip('/') + '/sources_to_targets',
                                  json={'sources': coords, 'targets': coords, 'costing': 'truck', 'units': 'kilometers'}, timeout=2)
            response.raise_for_status()
            rows = response.json()['sources_to_targets']
            payload = {'distance': [[v['distance'] for v in row] for row in rows],
                       'minutes': [[v['time']/60 for v in row] for row in rows]}
            result = parse(payload, 'Valhalla')
            cache_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload))
            return result
        except (httpx.HTTPError, ValueError, KeyError, TypeError, OSError):
            warnings.warn('Valhalla unavailable or invalid response; using Demo Fallback.')
    return fallback(s)
