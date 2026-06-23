"""
============================================================
MINI TEMPLATE — HANA Connection via .env (Local Dev)
============================================================
Use this when: running locally and credentials are in a .env file.

Setup:
  1. Copy .env.example → .env and fill in your credentials
  2. pip install hdbcli python-dotenv
  3. python connect_env.py
============================================================
"""

import os
from dotenv import load_dotenv
from hdbcli import dbapi

# Load .env file
load_dotenv()

# ── Required variables in your .env ──────────────────────
# HANA_HOST=your-host.hanacloud.ondemand.com
# HANA_PORT=443
# HANA_USER=DBADMIN
# HANA_PASSWORD=YourPassword
# HANA_CERTIFICATE=          ← optional, leave blank if not needed
# ─────────────────────────────────────────────────────────

def connect() -> dbapi.Connection:
    """Connect to HANA Cloud using .env credentials."""

    required = ["HANA_HOST", "HANA_PORT", "HANA_USER", "HANA_PASSWORD"]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        raise EnvironmentError(
            f"Missing in .env: {missing}\n"
            "See .env.example for reference."
        )

    conn = dbapi.connect(
        address=os.getenv("HANA_HOST"),
        port=int(os.getenv("HANA_PORT", 443)),
        user=os.getenv("HANA_USER"),
        password=os.getenv("HANA_PASSWORD"),
        encrypt="true",
        sslTrustStore=os.getenv("HANA_CERTIFICATE", ""),
    )
    print(f"✅ Connected to HANA → {os.getenv('HANA_HOST')}")
    return conn


if __name__ == "__main__":
    conn = connect()

    # Quick test query
    cursor = conn.cursor()
    cursor.execute("SELECT CURRENT_UTCTIMESTAMP FROM DUMMY")
    print("HANA Timestamp:", cursor.fetchone()[0])

    cursor.close()
    conn.close()
    print("🔒 Connection closed.")
