"""
============================================================
TEMPLATE 01 — SAP HANA Cloud: Connect & Health Check
============================================================
Supports two environments automatically:
  - Local development  → reads credentials from .env file
  - SAP BTP / Cloud Foundry → reads from bound HANA service

Dependencies:
    pip install hdbcli hana-ml cfenv python-dotenv

Usage:
    python hana_connection.py
============================================================
"""

import os
import logging
from dotenv import load_dotenv
from cfenv import AppEnv
from hdbcli import dbapi
import hana_ml

# ─────────────────────────────────────────────
# 1. LOGGING SETUP
# ─────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 2. ENVIRONMENT DETECTION
# ─────────────────────────────────────────────
load_dotenv()               # loads .env when running locally (no-op in CF)
cf_env = AppEnv()           # reads VCAP_SERVICES when running in Cloud Foundry

IS_LOCAL = cf_env.name is None   # True → local machine, False → Cloud Foundry


# ─────────────────────────────────────────────
# 3. RESOLVE HANA CREDENTIALS
# ─────────────────────────────────────────────
def get_hana_credentials() -> dict:
    """
    Returns a dict with keys: host, port, user, password, certificate.
    Works transparently for local and Cloud Foundry environments.
    """
    if IS_LOCAL:
        log.info("Environment: LOCAL — reading credentials from .env")

        # Validate that required variables are set
        required = ["HANA_HOST", "HANA_PORT", "HANA_USER", "HANA_PASSWORD"]
        missing = [v for v in required if not os.getenv(v)]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {missing}\n"
                "Add them to your .env file. See .env.example for reference."
            )

        return {
            "host":        os.getenv("HANA_HOST"),
            "port":        int(os.getenv("HANA_PORT", 443)),
            "user":        os.getenv("HANA_USER"),
            "password":    os.getenv("HANA_PASSWORD"),
            "certificate": os.getenv("HANA_CERTIFICATE", ""),   # optional
        }
    else:
        log.info("Environment: CLOUD FOUNDRY — reading credentials from bound service")

        # ── Change "hana" to match your CF service label if different ──
        CF_SERVICE_LABEL = "hana"
        svc = cf_env.get_service(label=CF_SERVICE_LABEL)

        if svc is None:
            raise EnvironmentError(
                f"HANA service '{CF_SERVICE_LABEL}' not found in VCAP_SERVICES.\n"
                "Check: cf services  →  confirm the service label."
            )

        return {
            "host":        svc.credentials["host"],
            "port":        int(svc.credentials.get("port", 443)),
            "user":        svc.credentials["user"],
            "password":    svc.credentials["password"],
            "certificate": svc.credentials.get("certificate", ""),
        }


# ─────────────────────────────────────────────
# 4. CONNECTION FACTORY
# ─────────────────────────────────────────────
def get_dbapi_connection(creds: dict) -> dbapi.Connection:
    """
    Opens a low-level hdbcli connection.
    Use this for raw SQL queries and cursor-based operations.
    """
    conn = dbapi.connect(
        address=creds["host"],
        port=creds["port"],
        user=creds["user"],
        password=creds["password"],
        encrypt="true",
        sslTrustStore=creds["certificate"],
    )
    log.info("hdbcli connection established → %s:%s", creds["host"], creds["port"])
    return conn


def get_hana_ml_connection(creds: dict) -> hana_ml.dataframe.ConnectionContext:
    """
    Opens a hana-ml ConnectionContext.
    Use this for DataFrame operations, ML algorithms, and PAL functions.
    """
    conn_ctx = hana_ml.dataframe.ConnectionContext(
        address=creds["host"],
        port=creds["port"],
        user=creds["user"],
        password=creds["password"],
        encrypt="true",
        sslValidateCertificate="false",
    )
    log.info("hana-ml ConnectionContext established → %s:%s", creds["host"], creds["port"])
    return conn_ctx


# ─────────────────────────────────────────────
# 5. HEALTH CHECK
# ─────────────────────────────────────────────
def health_check(conn: dbapi.Connection) -> dict:
    """
    Runs a lightweight query against HANA DUMMY table.
    Returns a dict with status, DB timestamp, and HANA version.

    Returns:
        {
            "status":    "OK" | "FAILED",
            "timestamp": "<HANA UTC timestamp>",
            "version":   "<HANA version string>",
            "error":     None | "<error message>"
        }
    """
    result = {"status": "FAILED", "timestamp": None, "version": None, "error": None}
    cursor = None

    try:
        cursor = conn.cursor()

        # Check 1: DB is alive — get current UTC timestamp
        cursor.execute("SELECT CURRENT_UTCTIMESTAMP FROM DUMMY")
        row = cursor.fetchone()
        result["timestamp"] = str(row["CURRENT_UTCTIMESTAMP"])

        # Check 2: Get HANA version
        cursor.execute("SELECT VALUE FROM M_SYSTEM_OVERVIEW WHERE NAME = 'Version'")
        row = cursor.fetchone()
        result["version"] = str(row["VALUE"]) if row else "Unknown"

        result["status"] = "OK"
        log.info("Health check PASSED | Timestamp: %s | Version: %s",
                 result["timestamp"], result["version"])

    except Exception as e:
        result["error"] = str(e)
        log.error("Health check FAILED: %s", e)

    finally:
        if cursor:
            cursor.close()

    return result


# ─────────────────────────────────────────────
# 6. MAIN — run standalone
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  SAP HANA Cloud — Connection Health Check")
    print("=" * 50)

    # Step 1: Resolve credentials
    creds = get_hana_credentials()

    # Step 2: Open connections
    conn    = get_dbapi_connection(creds)
    conn_ml = get_hana_ml_connection(creds)

    # Step 3: Health check
    result = health_check(conn)

    print("\nHealth Check Result:")
    print(f"  Status    : {result['status']}")
    print(f"  Timestamp : {result['timestamp']}")
    print(f"  Version   : {result['version']}")
    if result["error"]:
        print(f"  Error     : {result['error']}")

    # Step 4: Clean up
    conn.close()
    conn_ml.connection.close()
    print("\nConnections closed.")
    print("=" * 50 + "\n")
