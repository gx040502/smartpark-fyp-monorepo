"""
SmartPark AI Agent — Text-to-SQL Evaluation Harness
Benchmarks the QWEN Text-to-SQL pipeline against a manually verified reference dataset.

Supports two inference providers:
  PROVIDER=huggingface  -> HuggingFace Inference API (quota-limited)
  PROVIDER=ollama       -> local Ollama server (free, slower)

Usage:
    python evaluate.py                 # full run
    python evaluate.py --limit 3       # smoke test
    python evaluate.py --run-label R2  # second consistency run
"""

import os
import re
import csv
import time
import json
import argparse
import statistics
from datetime import datetime, date, timedelta
from decimal import Decimal

import pymysql
import requests
from dotenv import load_dotenv

from schema_context import SCHEMA_CONTEXT
from eval_dataset import DATASET

# ==========================================
# CONFIGURATION
# ==========================================
load_dotenv()

PROVIDER = os.getenv("PROVIDER", "huggingface").lower()
HF_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN", "")
MODEL_ID = os.getenv("MODEL_ID", "Qwen/Qwen2.5-Coder-7B-Instruct")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USERNAME", "root")
DB_PASS = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_DATABASE", "fyp_parking")

SQL_TEMPERATURE = 0.1
SQL_MAX_TOKENS = 300

# Markers that identify infrastructure problems rather than model errors.
INFRA_MARKERS = [
    "402", "429", "503", "504", "payment required", "rate limit",
    "depleted", "too many requests", "timed out", "timeout",
    "connection refused", "connection error", "max retries",
    "service unavailable", "quota", "insufficient credit",
]

if PROVIDER == "huggingface":
    from huggingface_hub import InferenceClient
    hf_client = InferenceClient(token=HF_TOKEN)


# ==========================================
# SQL EXTRACTION / VALIDATION
# (mirrors ai-service/main.py so the harness tests production behaviour)
# ==========================================
def extract_sql(text: str):
    m = re.search(r"```sql\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\s*(SELECT.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"(SELECT\s+.+?;)", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"(SELECT\s+.+?)(?:\n\n|$)", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def validate_sql(sql: str) -> bool:
    n = sql.strip().upper()
    if not (n.startswith("SELECT") or n.startswith("WITH")):
        return False
    for kw in ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
               "CREATE", "TRUNCATE", "GRANT", "REVOKE"]:
        if re.search(rf"\b{kw}\b", n):
            return False
    return True


def generate_sql_prompt(user_question: str) -> str:
    return f"""{SCHEMA_CONTEXT}

### Instructions
Given the database schema above, generate a MySQL SELECT query to answer the user's question.
- ONLY generate SELECT queries. Never generate INSERT, UPDATE, DELETE, DROP, or any data-modifying statement.
- Return ONLY the SQL query inside a ```sql code block.
- If the question cannot be answered with the available tables, explain why.
- Use proper MySQL syntax.

### User Question
{user_question}

### SQL Query
"""


def is_infra_error(msg: str) -> bool:
    low = msg.lower()
    return any(m in low for m in INFRA_MARKERS)


# ==========================================
# INFERENCE PROVIDERS
# ==========================================
def call_huggingface(prompt: str) -> str:
    completion = hf_client.chat_completion(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": "You are a SQL expert. Generate only MySQL SELECT queries."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=SQL_MAX_TOKENS,
        temperature=SQL_TEMPERATURE,
    )
    return completion.choices[0].message.content or ""


def call_ollama(prompt: str) -> str:
    resp = requests.post(
        f"{OLLAMA_URL}/v1/chat/completions",
        json={
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": "You are a SQL expert. Generate only MySQL SELECT queries."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": SQL_MAX_TOKENS,
            "temperature": SQL_TEMPERATURE,
        },
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"] or ""


def call_model(prompt: str) -> str:
    if PROVIDER == "ollama":
        return call_ollama(prompt)
    return call_huggingface(prompt)


def active_model_name() -> str:
    return OLLAMA_MODEL if PROVIDER == "ollama" else MODEL_ID


# ==========================================
# DATABASE
# ==========================================
def get_connection():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASS, database=DB_NAME,
        cursorclass=pymysql.cursors.Cursor, autocommit=True,
    )


def run_query(conn, sql):
    """Returns (rows, column_names, error)."""
    try:
        with conn.cursor() as cur:
            cur.execute(sql.rstrip().rstrip(";"))
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
            return rows, cols, None
    except Exception as e:
        return None, None, f"{type(e).__name__}: {e}"


# ==========================================
# RESULT-SET COMPARISON
# ==========================================
def normalise_value(v):
    if v is None:
        return "NULL"
    if isinstance(v, Decimal):
        return f"{float(v):.2f}"
    if isinstance(v, float):
        return f"{v:.2f}"
    if isinstance(v, (datetime, date, timedelta)):
        return str(v)
    return str(v).strip()


def normalise_rows(rows):
    return [tuple(normalise_value(v) for v in row) for row in rows]


def is_order_sensitive(reference_sql: str) -> bool:
    """Order matters only when the reference query explicitly orders results."""
    return bool(re.search(r"\bORDER\s+BY\b", reference_sql, re.IGNORECASE))


def compare_results(gen_rows, gen_cols, ref_rows, ref_cols, order_sensitive):
    """
    Returns (matched: bool, mode: str).
    'mode' is recorded per case so every adjudication is auditable.
    """
    g_norm = [c.strip().lower() for c in (gen_cols or [])]
    r_norm = [c.strip().lower() for c in (ref_cols or [])]

    if len(gen_rows) != len(ref_rows):
        return False, "row_count_mismatch"

    # Preferred: reference columns are a subset of generated columns.
    if r_norm and all(c in g_norm for c in r_norm):
        idx = [g_norm.index(c) for c in r_norm]
        projected = [tuple(row[i] for i in idx) for row in gen_rows]
        a, b = normalise_rows(projected), normalise_rows(ref_rows)
        ok = (a == b) if order_sensitive else (sorted(a) == sorted(b))
        mode = "exact" if len(g_norm) == len(r_norm) else "column_superset"
        return ok, mode

    # Fallback: aliases differ but arity matches — compare positionally.
    if len(g_norm) == len(r_norm):
        a, b = normalise_rows(gen_rows), normalise_rows(ref_rows)
        ok = (a == b) if order_sensitive else (sorted(a) == sorted(b))
        return ok, "positional"

    return False, "column_mismatch"


# ==========================================
# SINGLE TEST CASE
# ==========================================
def evaluate_case(conn, case):
    result = {
        "id": case["id"],
        "category": case["category"],
        "context": case["context"],
        "question": case["question"],
        "reference_sql": case["reference_sql"],
        "generated_sql": "",
        "verdict": "Fail",
        "failure_type": "",
        "detail": "",
        "match_mode": "",
        "returned_all_columns": False,
        "trivial_zero_row": False,
        "llm_latency_s": 0.0,
        "total_latency_s": 0.0,
        "gen_row_count": None,
        "ref_row_count": None,
    }

    t_start = time.perf_counter()

    # ---- Step 1: SQL generation ----  [PATCH A]
    try:
        t_llm = time.perf_counter()
        raw = call_model(generate_sql_prompt(case["question"]))
        result["llm_latency_s"] = round(time.perf_counter() - t_llm, 3)
    except Exception as e:
        msg = str(e)
        if is_infra_error(msg):
            result["verdict"] = "InfraError"
            result["failure_type"] = "InfraError"
            result["detail"] = f"Inference unavailable (excluded from accuracy): {msg[:200]}"
        else:
            result["failure_type"] = "Syntactic"
            result["detail"] = f"LLM request failed: {msg[:200]}"
        result["total_latency_s"] = round(time.perf_counter() - t_start, 3)
        return result

    generated = extract_sql(raw)
    if not generated:
        result["failure_type"] = "Syntactic"
        result["detail"] = "No SQL statement could be extracted from the model output."
        result["generated_sql"] = raw[:400]
        result["total_latency_s"] = round(time.perf_counter() - t_start, 3)
        return result

    result["generated_sql"] = generated

    if not validate_sql(generated):
        result["failure_type"] = "Syntactic"
        result["detail"] = "Rejected by validate_sql (non-SELECT or restricted keyword)."
        result["total_latency_s"] = round(time.perf_counter() - t_start, 3)
        return result

    # ---- Step 2: execute generated ----
    gen_rows, gen_cols, gen_err = run_query(conn, generated)
    if gen_err:
        result["failure_type"] = "Syntactic"
        result["detail"] = f"Execution error: {gen_err}"
        result["total_latency_s"] = round(time.perf_counter() - t_start, 3)
        return result

    # ---- Step 3: execute reference ----
    ref_rows, ref_cols, ref_err = run_query(conn, case["reference_sql"])
    if ref_err:
        result["verdict"] = "HarnessError"
        result["failure_type"] = "HarnessError"
        result["detail"] = f"REFERENCE SQL FAILED — fix the dataset: {ref_err}"
        result["total_latency_s"] = round(time.perf_counter() - t_start, 3)
        return result

    result["gen_row_count"] = len(gen_rows)
    result["ref_row_count"] = len(ref_rows)
    result["trivial_zero_row"] = (len(ref_rows) == 0)          # [PATCH D]
    result["returned_all_columns"] = bool(gen_cols and len(gen_cols) > len(ref_cols or []))

    # ---- Step 4: compare ----
    ordered = is_order_sensitive(case["reference_sql"])
    matched, mode = compare_results(gen_rows, gen_cols, ref_rows, ref_cols, ordered)
    result["match_mode"] = mode

    if matched:
        result["verdict"] = "Pass"
        note = " Generated query returned additional columns beyond those requested." \
               if mode == "column_superset" else ""
        result["detail"] = (f"Result sets equivalent ({len(ref_rows)} rows, "
                            f"{'order-sensitive' if ordered else 'order-insensitive'}, "
                            f"match mode: {mode}).{note}")
    else:
        result["failure_type"] = "Semantic"
        result["detail"] = (f"Executed successfully but result set mismatched "
                            f"(match mode: {mode}). Generated {len(gen_rows)} rows "
                            f"vs reference {len(ref_rows)} rows.")

    result["total_latency_s"] = round(time.perf_counter() - t_start, 3)
    return result


# ==========================================
# REPORTING
# ==========================================
def print_report(results, run_label, aborted=False):
    # [PATCH C] Infrastructure errors excluded from the accuracy denominator.
    infra = [r for r in results if r["verdict"] == "InfraError"]
    harness = [r for r in results if r["verdict"] == "HarnessError"]
    scored = [r for r in results if r["verdict"] not in ("InfraError", "HarnessError")]

    total = len(scored)
    passed = [r for r in scored if r["verdict"] == "Pass"]
    syntactic = [r for r in scored if r["failure_type"] == "Syntactic"]
    semantic = [r for r in scored if r["failure_type"] == "Semantic"]
    superset = [r for r in scored if r.get("match_mode") == "column_superset"]
    trivial = [r for r in scored if r.get("trivial_zero_row")]

    print("\n" + "=" * 78)
    print(f"  SMARTPARK TEXT-TO-SQL EVALUATION — RUN {run_label}")
    print("=" * 78)
    print(f"  Provider         : {PROVIDER}")
    print(f"  Model            : {active_model_name()}")
    print(f"  Temperature      : {SQL_TEMPERATURE}   Max tokens: {SQL_MAX_TOKENS}")
    print(f"  Database         : {DB_NAME}@{DB_HOST}:{DB_PORT}")
    print(f"  Timestamp        : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Cases attempted  : {len(results)}")
    print(f"  Cases scored     : {total}")

    if aborted:
        print("\n  !! RUN ABORTED — repeated inference failures. FIGURES ARE NOT VALID.")
    if infra:
        print(f"\n  !! {len(infra)} case(s) excluded — inference unavailable.")
        print("     RUN IS INCOMPLETE. Restore inference capacity and re-run.")
    if harness:
        print("\n  !! HARNESS ERRORS — reference SQL failed to execute:")
        for r in harness:
            print(f"     {r['id']}: {r['detail'][:110]}")
        print("     Fix the dataset before reporting results.")

    if total == 0:
        print("\n  No scoreable cases. Nothing to report.\n")
        return

    print("\n" + "-" * 78)
    print("  OVERALL ACCURACY")
    print("-" * 78)
    print(f"  Passed : {len(passed)}/{total}  ({len(passed)/total*100:.2f}%)")
    print(f"  Failed : {total - len(passed)}/{total}")
    print(f"    - Syntactic failures : {len(syntactic)}")
    print(f"    - Semantic failures  : {len(semantic)}")
    print(f"  Passes returning extra columns  : {len(superset)}")
    print(f"  Cases with empty reference set  : {len(trivial)}  (low evidential value)")

    print("\n" + "-" * 78)
    print("  ACCURACY BY COMPLEXITY CATEGORY")
    print("-" * 78)
    print(f"  {'Category':<10}{'Passed':>8}{'Total':>8}{'Accuracy':>12}{'Syn':>6}{'Sem':>6}")
    for cat in ["Easy", "Medium", "Hard"]:
        sub = [r for r in scored if r["category"] == cat]
        if not sub:
            continue
        p = len([r for r in sub if r["verdict"] == "Pass"])
        s_syn = len([r for r in sub if r["failure_type"] == "Syntactic"])
        s_sem = len([r for r in sub if r["failure_type"] == "Semantic"])
        print(f"  {cat:<10}{p:>8}{len(sub):>8}{p/len(sub)*100:>11.2f}%{s_syn:>6}{s_sem:>6}")

    print("\n" + "-" * 78)
    print("  RESPONSE LATENCY (NFR3 — target < 5.00 s)")
    print("-" * 78)
    lat = [r["llm_latency_s"] for r in scored if r["llm_latency_s"] > 0]
    if lat:
        breaches = len([x for x in lat if x > 5.0])
        print(f"  Mean   : {statistics.mean(lat):.3f} s")
        print(f"  Median : {statistics.median(lat):.3f} s")
        print(f"  Min    : {min(lat):.3f} s")
        print(f"  Max    : {max(lat):.3f} s")
        if len(lat) > 1:
            print(f"  StdDev : {statistics.stdev(lat):.3f} s")
        print(f"  Cases exceeding 5.00 s : {breaches}/{len(lat)}")

    print("\n" + "-" * 78)
    print("  PER-CASE VERDICTS")
    print("-" * 78)
    print(f"  {'ID':<6}{'Cat':<8}{'Verdict':<12}{'Type':<12}{'Lat(s)':>8}  Detail")
    for r in results:
        print(f"  {r['id']:<6}{r['category']:<8}{r['verdict']:<12}"
              f"{r['failure_type'] or '-':<12}{r['llm_latency_s']:>8.2f}  {r['detail'][:55]}")

    print("\n" + "-" * 78)
    print("  FAILURE DETAIL (for Section 7.8.4)")
    print("-" * 78)
    fails = [r for r in scored if r["verdict"] != "Pass"]
    if not fails:
        print("  No failures recorded.")
    for r in fails:
        print(f"\n  [{r['id']}] {r['category']} — {r['failure_type']}")
        print(f"  Question  : {r['question']}")
        print(f"  Generated : {' '.join(r['generated_sql'].split())}")
        print(f"  Reference : {' '.join(r['reference_sql'].split())}")
        print(f"  Detail    : {r['detail']}")

    print("\n" + "=" * 78)
    print("  END OF REPORT — copy everything above")
    print("=" * 78 + "\n")


def write_csv(results, run_label):
    cols = ["id", "category", "context", "question", "reference_sql", "generated_sql",
            "verdict", "failure_type", "detail", "match_mode", "returned_all_columns",
            "trivial_zero_row", "llm_latency_s", "total_latency_s",
            "gen_row_count", "ref_row_count"]

    fname = f"evaluation_results_{run_label}.csv"
    with open(fname, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k, "") for k in cols})
    print(f"[saved] {fname}")

    jname = f"evaluation_results_{run_label}.json"
    with open(jname, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"[saved] {jname}")


# ==========================================
# MAIN
# ==========================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="only run first N cases")
    parser.add_argument("--run-label", type=str, default="R1", help="label for this run")
    args = parser.parse_args()

    cases = DATASET[:args.limit] if args.limit else DATASET

    # Pre-flight checks
    if PROVIDER == "huggingface" and not HF_TOKEN:
        print("ERROR: HUGGINGFACE_API_TOKEN not set in .env")
        return
    if PROVIDER == "ollama":
        try:
            requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).raise_for_status()
        except Exception as e:
            print(f"ERROR: cannot reach Ollama at {OLLAMA_URL} — {e}")
            print("Start it with: ollama serve")
            return

    try:
        conn = get_connection()
    except Exception as e:
        print(f"ERROR: cannot connect to MySQL — {e}")
        return

    print(f"Provider: {PROVIDER} | Model: {active_model_name()}")
    print(f"Running {len(cases)} test cases ...")

    results = []
    consecutive_infra = 0
    aborted = False

    for i, case in enumerate(cases, 1):
        print(f"  [{i}/{len(cases)}] {case['id']} ({case['category']}) ...", end=" ", flush=True)
        r = evaluate_case(conn, case)
        print(f"{r['verdict']}" + (f" ({r['failure_type']})" if r["failure_type"]
                                   and r["failure_type"] != r["verdict"] else ""))
        results.append(r)

        # [PATCH B] Abort rather than silently poisoning the remaining cases.
        if r["verdict"] == "InfraError":
            consecutive_infra += 1
            if consecutive_infra >= 3:
                print("\n  ABORTED: 3 consecutive inference failures.")
                print("  Restore inference capacity and re-run — this run is NOT valid.")
                aborted = True
                break
        else:
            consecutive_infra = 0

        time.sleep(0.5)

    conn.close()
    print_report(results, args.run_label, aborted=aborted)
    write_csv(results, args.run_label)


if __name__ == "__main__":
    main()