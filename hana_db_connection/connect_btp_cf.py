"""
============================================================
MINI TEMPLATE — HANA Connection via BTP Cloud Foundry
============================================================
Use this when: your app is deployed on SAP BTP and HANA is
bound as a service (credentials come from VCAP_SERVICES).

Setup:
  1. Bind your HANA service in BTP: cf bind-service <app> <hana-service>
  2. pip install hdbcli cfenv
  3. python connect_btp_cf.py   (run inside CF environment)

Note: CF_SERVICE_LABEL must match your bound service label.
      Check with: cf services  (look at the "service" column)
============================================================
"""

from cfenv import AppEnv
from hdbcli import dbapi

# ── Change this to match your CF HANA service label ──────
CF_SERVICE_LABEL = "hana"
# ─────────────────────────────────────────────────────────


def connect() -> dbapi.Connection:
    """Connect to HANA Cloud using BTP Cloud Foundry bound service."""

    cf_env = AppEnv()
    svc = cf_env.get_service(label=CF_SERVICE_LABEL)

    if svc is None:
        raise EnvironmentError(
            f"HANA service '{CF_SERVICE_LABEL}' not found in VCAP_SERVICES.\n"
            "Run: cf services  →  check the service label and try again."
        )

    creds = svc.credentials
    conn = dbapi.connect(
        address=creds["host"],
        port=int(creds.get("port", 443)),
        user=creds["user"],
        password=creds["password"],
        encrypt="true",
        sslTrustStore=creds.get("certificate", ""),
    )
    print(f"✅ Connected to HANA via BTP CF → {creds['host']}")
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
