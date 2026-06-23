"""
============================================================
SAMPLE PROJECT — One-Time Setup Script
============================================================
Run this ONCE before launching app.py.

What it does:
  1. Creates SAMPLE_EMPLOYEES table in HANA and inserts 10 rows
  2. Embeds a company FAQ document into HANA vector store
     (used by the RAG tab in the app)

Run:
    python setup_sample_data.py

Requires:
  - .env file with HANA credentials + OPENAI_API_KEY
  - pip install -r requirements.txt
============================================================
"""

import sys, os, pathlib

# ── Add sibling template folders to path ─────────────────
ROOT = pathlib.Path(__file__).parent.parent
sys.path.extend([
    str(ROOT / "hana_db_connection"),
    str(ROOT / "hana_vector_store_openai"),
])

from dotenv import load_dotenv
load_dotenv()

from connect_env import connect
from vector_table import create_vector_table
from embed_and_store import embed_and_store
from embedding_setup import get_embedding_model
from langchain_core.documents import Document


# ── 1. HANA connection ────────────────────────────────────
print("🔌 Connecting to HANA...")
conn = connect()
cursor = conn.cursor()
print("✅ Connected\n")


# ── 2. Create SAMPLE_EMPLOYEES table ─────────────────────
print("📋 Creating SAMPLE_EMPLOYEES table...")
cursor.execute("DROP TABLE SAMPLE_EMPLOYEES IF EXISTS")
cursor.execute("""
    CREATE TABLE SAMPLE_EMPLOYEES (
        ID          INT PRIMARY KEY,
        NAME        NVARCHAR(100),
        DEPARTMENT  NVARCHAR(50),
        ROLE        NVARCHAR(100),
        SALARY      INT,
        HIRE_DATE   DATE,
        LOCATION    NVARCHAR(50)
    )
""")

employees = [
    (1,  "Alice Johnson",   "Engineering",  "Senior Developer",    95000, "2021-03-15", "Bangalore"),
    (2,  "Bob Smith",       "Engineering",  "Junior Developer",    55000, "2023-06-01", "Hyderabad"),
    (3,  "Carol White",     "HR",           "HR Manager",          75000, "2019-09-10", "Mumbai"),
    (4,  "David Lee",       "Sales",        "Sales Executive",     60000, "2022-01-20", "Delhi"),
    (5,  "Eva Brown",       "Sales",        "Sales Manager",       85000, "2020-04-05", "Bangalore"),
    (6,  "Frank Miller",    "Finance",      "Finance Analyst",     70000, "2021-11-30", "Pune"),
    (7,  "Grace Kim",       "Engineering",  "Tech Lead",          110000, "2018-07-22", "Bangalore"),
    (8,  "Henry Davis",     "HR",           "Recruiter",           50000, "2023-02-14", "Mumbai"),
    (9,  "Iris Chen",       "Finance",      "CFO",                150000, "2016-05-01", "Bangalore"),
    (10, "James Wilson",    "Sales",        "Business Dev",        80000, "2022-08-15", "Delhi"),
]

cursor.executemany(
    "INSERT INTO SAMPLE_EMPLOYEES VALUES (?,?,?,?,?,?,?)",
    employees
)
conn.commit()
print(f"✅ Inserted {len(employees)} employees into SAMPLE_EMPLOYEES\n")


# ── 3. Embed company FAQ into HANA vector store ───────────
VECTOR_TABLE = os.getenv("VECTOR_TABLE_NAME", "VECTOR_STORE")
EMBEDDING_DIM = 1536  # text-embedding-3-small default

print(f"📚 Setting up vector store: {VECTOR_TABLE}")
create_vector_table(conn, table_name=VECTOR_TABLE, dimension=EMBEDDING_DIM)

# Company FAQ document — the RAG tab will answer questions about this
company_faq = """
TECHCORP COMPANY HANDBOOK — FREQUENTLY ASKED QUESTIONS

WORK FROM HOME POLICY
Employees may work from home up to 3 days per week. Full-time remote work requires
manager approval and is reviewed every 6 months. Remote employees must be available
during core hours: 10 AM to 4 PM IST. Equipment for home setup (laptop, headset)
is provided by the company.

LEAVE POLICY
Annual Leave: All employees receive 18 days of paid annual leave per year.
Sick Leave: 12 days of sick leave per year, no carry-forward.
Maternity Leave: 26 weeks of fully paid leave.
Paternity Leave: 2 weeks of fully paid leave.
Leave must be applied for at least 2 days in advance except for emergencies.

PERFORMANCE REVIEWS
Performance reviews are conducted twice a year — in June and December.
Ratings: Exceptional (5), Exceeds Expectations (4), Meets Expectations (3),
Needs Improvement (2), Unsatisfactory (1). Ratings 4 and above are eligible
for year-end bonuses. Ratings 2 and below trigger a Performance Improvement Plan.

SALARY & COMPENSATION
Salaries are reviewed annually in January. Increments are based on performance
rating and market benchmarking. Employees rated 4 or above receive a minimum
5% increment. Bonuses are paid in February for the previous year's performance.

BENEFITS
Health Insurance: Employees and immediate family are covered up to ₹5 lakhs per year.
Provident Fund: 12% of basic salary contributed by both employee and company.
Learning Budget: ₹30,000 per year per employee for courses, certifications, or books.
Gym Reimbursement: Up to ₹5,000 per month.

ONBOARDING
New employees go through a 2-week onboarding program. Week 1 covers company
culture, tools, and HR processes. Week 2 is team-specific technical onboarding.
A buddy is assigned to every new joiner for the first 3 months.

TRAVEL POLICY
Business travel requires manager approval. Economy class for flights under 4 hours.
Business class for flights over 4 hours or international travel. Hotel budget:
₹8,000/night in metro cities, ₹5,000/night in other cities. All expenses must
be submitted within 7 days of return.

IT & SECURITY
Employees must change passwords every 90 days. VPN is mandatory for remote access.
No personal devices for work email without MDM enrollment. Data must not be stored
on personal cloud services (Google Drive, Dropbox, etc.). Report security incidents
to security@techcorp.com within 1 hour of discovery.
"""

docs = [Document(page_content=company_faq, metadata={"source": "company_faq", "type": "text"})]
embedding_model = get_embedding_model()

embed_and_store(
    conn=conn,
    documents=docs,
    embedding_model=embedding_model,
    table_name=VECTOR_TABLE,
    chunk_size=400,
    chunk_overlap=50,
)
print(f"✅ Company FAQ embedded into {VECTOR_TABLE}\n")


# ── Done ──────────────────────────────────────────────────
cursor.close()
conn.close()

print("=" * 55)
print("✅ Setup complete! Now run:")
print("   streamlit run app.py")
print("=" * 55)
