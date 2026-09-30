"""
Smart Parking AI Agent — Text-to-SQL Evaluation Harness (DATA-DIFF VERSION)
Benchmarks the QWEN Text-to-SQL pipeline against a manually verified reference dataset.

WHAT'S DIFFERENT FROM evaluate.py:
  The original harness compares gen_rows vs ref_rows and, the moment the ROW
  COUNTS differ, immediately records "row_count_mismatch" and stops — it never
  looks at what the actual data was. That tells you THAT a case failed, but
  not WHY (which rows are missing, which are unexpected extras).

  This version always fetches both result sets in full and computes a real
  set-diff on the actual normalised row values:
    - missing_rows : rows the reference expected but the generated query
                      did not return (false negatives)
    - extra_rows    : rows the generated query returned that the reference
                      did not expect (false positives)
  Both are persisted in the JSON/CSV output so failures can be diagnosed
  from the report alone, without re-running anything.

Supports two inference providers:
  PROVIDER=huggingface  -> HuggingFace Inference API (quota-limited)
  PROVIDER=ollama       -> local Ollama server (free, slower)

Usage:
    python evaluate_data_diff.py                 # full run
    python evaluate_data_diff.py --limit 3        # smoke test
    python evaluate_data_diff.py --run-label R4    # labelled run
"""

import os
import re
import csv
import time
import json
import argparse
import statistics
from collections import Counter
from datetime import datetime, date, timedelta
from decimal import Decimal

import pymysql
import requests
from dotenv import load_dotenv

from new_schema_context import SCHEMA_CONTEXT
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

# Cap how many mismatched rows we persist per case, so one runaway query
# (e.g. a missing WHERE clause) doesn't blow up the report with thousands
# of lines. Raise this if your dataset needs more.
MAX_DIFF_ROWS_STORED = 25

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
# DATA-LEVEL COMPARISON
# (this is the core change — everything here works on the actual fetched
#  rows, not on SQL text and not just on row counts)
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


def rows_to_dicts(rows, cols, limit=None):
    """Turn raw tuples into [{col: val, ...}] for readable JSON output."""
    out = []
    for row in rows[: limit if limit is not None else len(rows)]:
        out.append({c: normalise_value(v) for c, v in zip(cols, row)})
    return out


def is_order_sensitive(reference_sql: str) -> bool:
    """Order matters only when the reference query explicitly orders results."""
    return bool(re.search(r"\bORDER\s+BY\b", reference_sql, re.IGNORECASE))


def align_columns(gen_rows, gen_cols, ref_cols):
    """
    Figure out how to line up generated columns against reference columns
    so that value-level comparison is apples-to-apples. Returns
    (projected_rows_or_None, mode).
    """
    g_norm = [c.strip().lower() for c in (gen_cols or [])]
    r_norm = [c.strip().lower() for c in (ref_cols or [])]

    # Preferred: reference columns are a subset of generated columns
    # (model returned the right data, possibly plus extra columns).
    if r_norm and all(c in g_norm for c in r_norm):
        idx = [g_norm.index(c) for c in r_norm]
        projected = [tuple(row[i] for i in idx) for row in gen_rows]
        mode = "exact" if len(g_norm) == len(r_norm) else "column_superset"
        return projected, mode

    # Fallback: aliases differ but arity matches — compare positionally.
    if len(g_norm) == len(r_norm):
        return list(gen_rows), "positional"

    # Genuinely different shape — can't align columns at all.
    return None, "column_mismatch"


def diff_result_sets(gen_rows, gen_cols, ref_rows, ref_cols, order_sensitive):
    """
    THE CORE OF THIS SCRIPT.
    Always compares actual fetched data (never short-circuits on row count
    alone) and returns a rich diagnostic dict:
      matched        : bool
      mode           : how columns were aligned ('exact', 'column_superset',
                        'positional', 'column_mismatch')
      missing_rows   : rows present in reference but absent from generated
                        (capped at MAX_DIFF_ROWS_STORED, real values)
      extra_rows     : rows present in generated but absent from reference
                        (capped at MAX_DIFF_ROWS_STORED, real values)
    """
    projected, mode = align_columns(gen_rows, gen_cols, ref_cols)

    if projected is None:
        # Can't align columns — report full raw data on both sides so the
        # report can still show exactly what each side returned.
        return {
            "matched": False,
            "mode": mode,
            "missing_rows": rows_to_dicts(ref_rows, ref_cols, MAX_DIFF_ROWS_STORED),
            "extra_rows": rows_to_dicts(gen_rows, gen_cols, MAX_DIFF_ROWS_STORED),
        }

    gen_norm = normalise_rows(projected)
    ref_norm = normalise_rows(ref_rows)
    r_cols_for_display = ref_cols or gen_cols

    if order_sensitive:
        matched = gen_norm == ref_norm
        missing_tuples = [] if matched else [t for t in ref_norm if t not in gen_norm]
        extra_tuples = [] if matched else [t for t in gen_norm if t not in ref_norm]
    else:
        gen_counter, ref_counter = Counter(gen_norm), Counter(ref_norm)
        matched = gen_counter == ref_counter
        missing_tuples = list((ref_counter - gen_counter).elements())
        extra_tuples = list((gen_counter - ref_counter).elements())

    def tuples_to_dicts(tuples):
        return [dict(zip(r_cols_for_display, t)) for t in tuples[:MAX_DIFF_ROWS_STORED]]

    return {
        "matched": matched,
        "mode": mode,
        "missing_rows": tuples_to_dicts(missing_tuples),
        "extra_rows": tuples_to_dicts(extra_tuples),
    }


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
        "gen_row_count": None,
        "ref_row_count": None,
        # NEW: the actual fetched data and the actual diff, not just counts.
        "generated_data": [],
        "reference_data": [],
        "missing_rows": [],   # expected but not returned by generated SQL
        "extra_rows": [],     # returned by generated SQL but not expected
        "llm_latency_s": 0.0,
        "total_latency_s": 0.0,
    }

    t_start = time.perf_counter()

    # ---- Step 1: SQL generation ----
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

    # Always persist the actual fetched data (capped) — this is the whole
    # point of this version: the report should never need to guess.
    result["generated_data"] = rows_to_dicts(gen_rows, gen_cols, MAX_DIFF_ROWS_STORED)
    result["reference_data"] = rows_to_dicts(ref_rows, ref_cols, MAX_DIFF_ROWS_STORED)

    # ---- Step 4: diff actual data ----
    ordered = is_order_sensitive(case["reference_sql"])
    diff = diff_result_sets(gen_rows, gen_cols, ref_rows, ref_cols, ordered)

    result["match_mode"] = diff["mode"]
    result["missing_rows"] = diff["missing_rows"]
    result["extra_rows"] = diff["extra_rows"]

    if diff["matched"]:
        result["verdict"] = "Pass"
        note = (" Generated query returned additional columns beyond those requested."
                if diff["mode"] == "column_superset" else "")
        result["detail"] = (f"Result sets equivalent ({len(ref_rows)} rows, "
                            f"{'order-sensitive' if ordered else 'order-insensitive'}, "
                            f"match mode: {diff['mode']}).{note}")
    else:
        result["failure_type"] = "Semantic"
        n_missing, n_extra = len(diff["missing_rows"]), len(diff["extra_rows"])
        result["detail"] = (f"Data mismatch (match mode: {diff['mode']}). "
                            f"{n_missing} row(s) missing, {n_extra} unexpected row(s) returned. "
                            f"See 'missing_rows' / 'extra_rows' for actual values.")

    result["total_latency_s"] = round(time.perf_counter() - t_start, 3)
    return result


# ==========================================
# REPORTING
# ==========================================
def print_report(results, run_label, aborted=False):
    infra = [r for r in results if r["verdict"] == "InfraError"]
    harness = [r for r in results if r["verdict"] == "HarnessError"]
    scored = [r for r in results if r["verdict"] not in ("InfraError", "HarnessError")]

    total = len(scored)
    passed = [r for r in scored if r["verdict"] == "Pass"]
    syntactic = [r for r in scored if r["failure_type"] == "Syntactic"]
    semantic = [r for r in scored if r["failure_type"] == "Semantic"]

    print("\n" + "=" * 78)
    print(f"  SMARTPARK TEXT-TO-SQL EVALUATION (DATA-DIFF) — RUN {run_label}")
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
              f"{r['failure_type'] or '-':<12}{r['llm_latency_s']:>8.2f}  {r['detail'][:70]}")

    print("\n" + "-" * 78)
    print("  FAILURE DETAIL — ACTUAL DATA (for Section 7.8.4)")
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
        if r["missing_rows"]:
            print(f"  Missing rows (expected, not returned):")
            for row in r["missing_rows"]:
                print(f"     - {row}")
        if r["extra_rows"]:
            print(f"  Extra rows (returned, not expected):")
            for row in r["extra_rows"]:
                print(f"     - {row}")

    print("\n" + "=" * 78)
    print("  END OF REPORT — copy everything above")
    print("=" * 78 + "\n")


def write_csv(results, run_label):
    cols = ["id", "category", "context", "question", "reference_sql", "generated_sql",
            "verdict", "failure_type", "detail", "match_mode",
            "gen_row_count", "ref_row_count",
            "missing_rows", "extra_rows",
            "llm_latency_s", "total_latency_s"]

    fname = f"evaluation_results_{run_label}.csv"
    with open(fname, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in results:
            row = {k: r.get(k, "") for k in cols}
            # Flatten row-diff lists into readable strings for the CSV.
            row["missing_rows"] = json.dumps(r.get("missing_rows", []), default=str)
            row["extra_rows"] = json.dumps(r.get("extra_rows", []), default=str)
            w.writerow(row)
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