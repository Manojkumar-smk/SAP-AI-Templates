"""
============================================================
HANA Connection Helper — shared by rag.py and sql_query.py
============================================================
Same pattern as hana_db_connection/connect_env.py. This
service is STATELESS by design — it does NOT store conversation
history itself (see ARCHITECTURE.md: CAP owns that). It only
reads from HANA — for vector search (RAG) and ad-hoc business
table queries (SQL router).
============================================================
"""

import os
from dotenv import load_dotenv
from hdbcli import dbapi

load_dotenv()


def get_connection() -> dbapi.Connection:
    return dbapi.connect(
        address=os.getenv("HANA_HOST"),
        port=int(os.getenv("HANA_PORT", 443)),
        user=os.getenv("HANA_USER"),
        password=os.getenv("HANA_PASSWORD"),
        encrypt="true",
        sslTrustStore=os.getenv("HANA_CERTIFICATE", ""),
    )
