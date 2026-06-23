"""
============================================================
MINI TEMPLATE — HANA Connection via hana-ml (ConnectionContext)
============================================================
Use this when: you want to use hana-ml for DataFrame operations,
ML algorithms (PAL), or the HANA AI/ML functions.

This is DIFFERENT from hdbcli:
  - hdbcli     → raw SQL, cursor-based (connect_env.py / connect_btp_cf.py)
  - hana-ml    → DataFrame API, PAL, AutoML, vector store, etc.

Setup:
  1. Copy .env.example → .env and fill in your credentials
  2. pip install hana-ml python-dotenv
  3. python connect_hana_ml.py
============================================================
"""

import os
from dotenv import load_dotenv
import hana_ml.dataframe as dataframe

load_dotenv()


def connect() -> dataframe.ConnectionContext:
    """Open a hana-ml ConnectionContext using .env credentials."""

    required = ["HANA_HOST", "HANA_PORT", "HANA_USER", "HANA_PASSWORD"]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        raise EnvironmentError(f"Missing in .env: {missing}")

    cc = dataframe.ConnectionContext(
        address=os.getenv("HANA_HOST"),
        port=int(os.getenv("HANA_PORT", 443)),
        user=os.getenv("HANA_USER"),
        password=os.getenv("HANA_PASSWORD"),
        encrypt="true",
        sslValidateCertificate="false",
    )
    print(f"✅ hana-ml ConnectionContext ready → {os.getenv('HANA_HOST')}")
    return cc


if __name__ == "__main__":
    cc = connect()

    # Quick test: run a SQL statement via hana-ml
    result = cc.sql("SELECT CURRENT_UTCTIMESTAMP FROM DUMMY").collect()
    print("HANA Timestamp:", result.iloc[0, 0])

    # Example: list tables in current schema
    # tables = cc.sql("SELECT TABLE_NAME FROM TABLES WHERE SCHEMA_NAME = CURRENT_SCHEMA").collect()
    # print(tables)

    cc.close()
    print("🔒 ConnectionContext closed.")
