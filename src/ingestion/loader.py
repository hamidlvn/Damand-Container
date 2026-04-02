import pandas as pd
import logging
from pathlib import Path
from typing import Dict, Any, List

from src.schemas.pandera_schemas import RawIngestionSchema
from src.utils.config import load_config

# Setup explicit logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardizes column names to lowercase snake_case to match our strict schema."""
    df.columns = df.columns.str.lower().str.strip()
    return df

def validate_required_columns(df: pd.DataFrame, required_columns: List[str]) -> None:
    """Ensures all expected columns exist in the DataFrame."""
    missing = [col for col in required_columns if col.lower() not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in raw dataset: {missing}")

def clean_and_fill_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Handles missing values explicitly, enforcing TEU columns as numeric."""
    # Convert TEU columns to numeric, replacing any non-parsable strings with NaN
    teu_cols = ['empty_out_teu', 'empty_in_teu', 'full_out_teu', 'full_in_teu']
    for col in teu_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Count and log missing values before filling
            missing_count = df[col].isna().sum()
            if missing_count > 0:
                logger.warning(f"Found {missing_count} missing values in '{col}'. Assuming 0 TEU.")
                
            # Assume no activity where TEU is missing
            df[col] = df[col].fillna(0.0)

    # Convert date
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        missing_dates = df['date'].isna().sum()
        if missing_dates > 0:
            logger.warning(f"Found {missing_dates} unparsable dates. Dropping these rows.")
            df = df.dropna(subset=['date'])

    return df

def ingest_dataset(config: Dict[str, Any] = None) -> pd.DataFrame:
    """
    End-to-end ingestion logic: load, standardize, clean, and validate.
    """
    if config is None:
        config = load_config()

    ingestion_cfg = config.get("ingestion", {})
    raw_path = ingestion_cfg.get("raw_data_path")
    expected_cols = ingestion_cfg.get("required_columns", [])

    if not raw_path:
        raise ValueError("raw_data_path is missing from configuration")

    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    raw_path = PROJECT_ROOT / raw_path

    logger.info(f"Loading raw dataset from: {raw_path}")

    # Load raw CSV
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw data file not found: {raw_path}")
        
    df = pd.read_csv(raw_path)
    logger.info(f"Loaded {len(df)} rows from raw dataset.")

    # 1. Standardize
    df = standardize_columns(df)
    
    # 2. Validate early presence
    validate_required_columns(df, expected_cols)

    # 3. Handle Missing & Cast Numeric
    df = clean_and_fill_missing(df)

    # 4. Strict Pandera Validation (enforces no negative TEUs, missing ports, etc)
    logger.info("Executing strict Pandera schema validation...")
    validated_df = RawIngestionSchema.validate(df)

    # 5. Output processed data
    output_dir = Path(ingestion_cfg.get("processed_data_dir", "data/processed"))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    out_file = output_dir / ingestion_cfg.get("processed_file_name", "cleaned_history.parquet")
    validated_df.to_parquet(out_file, index=False)
    logger.info(f"Successfully saved validated dataset to: {out_file}")

    return validated_df
