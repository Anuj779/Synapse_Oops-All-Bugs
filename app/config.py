import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data' / 'sample_data'
ARTIFACT_DIR = ROOT / 'artifacts'
SEED = 42
FUEL_PRICE = float(os.getenv('FUEL_PRICE_INR', '95'))
CO2_FACTOR = float(os.getenv('CO2_KG_PER_LITRE', '2.68'))
MAX_OPTIMIZATION_ITERATIONS = max(1, min(6, int(os.getenv('MAX_OPTIMIZATION_ITERATIONS', '3'))))
RISK_MODES = {name: float(os.getenv(name.upper() + '_RISK', default)) for name, default in
              [('Economy', '.35'), ('Balanced', '.15'), ('Reliable', '.05')]}
START_HOUR = 8
