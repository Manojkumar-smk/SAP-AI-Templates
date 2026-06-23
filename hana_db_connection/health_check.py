"""
============================================================
MINI TEMPLATE — HANA Health Check
============================================================
Use this when: you have an hdbcli connection and want to
verify HANA is alive, get the timestamp, and check the version.

Works with any hdbcli connection — import connect() from
connect_env.py or connect_btp_cf.py and pass the connection in.
============================================================
"""

from hdbcli import dbapi


def health_check(conn: dbapi.Connection) -> dict:
    """
    Run a lightweight health check against HANA.

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

        # Check 1: DB alive → current UTC timestamp
        cursor.execute("SELECT CURRENT_UTCTIMESTAMP FROM DUMMY")
        result["timestamp"] = str(cursor.fetchone()[0])

        # Check 2: HANA version
        cursor.execute("SELECT VALUE FROM M_SYSTEM_OVERVIEW WHERE NAME = 'Version'")
        row = cursor.fetchone()
        result["version"] = str(row[0]) if row else "Unknown"

        result["status"] = "OK"

    except Exception as e:
        result["error"] = str(e)

    finally:
        if cursor:
            cursor.close()

    return result


if __name__ == "__main__":
    # ── Swap the import below to use BTP CF instead ───────
    from connect_env import connect
    # from connect_btp_cf import connect
    # ─────────────────────────────────────────────────────

    conn = connect()
    result = health_check(conn)

    print("\n── HANA Health Check ──────────────────")
    print(f"  Status    : {result['status']}")
    print(f"  Timestamp : {result['timestamp']}")
    print(f"  Version   : {result['version']}")
    if result["error"]:
        print(f"  Error     : {result['error']}")
    print("───────────────────────────────────────\n")

    conn.close()
