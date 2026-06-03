"""
SmartPark AI Agent — Text-to-SQL Service
FastAPI service that orchestrates LLM inference via HuggingFace
and SQL execution via the Laravel backend.
"""

import os
import re
import json
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
import httpx

from schema_context import SCHEMA_CONTEXT

# ==========================================
# CONFIGURATION
# ==========================================
load_dotenv()

HF_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN", "")
LARAVEL_API_URL = os.getenv("LARAVEL_API_URL", "http://127.0.0.1:8000/api")
MODEL_ID = os.getenv("MODEL_ID", "Qwen/Qwen2.5-Coder-7B-Instruct")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# FASTAPI APP
# ==========================================
app = FastAPI(title="SmartPark AI Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# HuggingFace Inference Client
hf_client = InferenceClient(token=HF_TOKEN)

# ==========================================
# REQUEST / RESPONSE MODELS
# ==========================================

class Message(BaseModel):
    role: str
    content: str

class GenerateRequest(BaseModel):
    messages: list[Message]

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def extract_sql(text: str) -> str | None:
    """Extract SQL query from LLM output."""
    # Try to find SQL in code blocks first
    sql_match = re.search(r"```sql\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if sql_match:
        return sql_match.group(1).strip()

    # Try to find SQL in generic code blocks
    code_match = re.search(r"```\s*(SELECT.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if code_match:
        return code_match.group(1).strip()

    # Try to find a raw SELECT statement
    select_match = re.search(r"(SELECT\s+.+?;)", text, re.DOTALL | re.IGNORECASE)
    if select_match:
        return select_match.group(1).strip()

    # Last resort: find SELECT without semicolon
    select_match2 = re.search(r"(SELECT\s+.+?)(?:\n\n|$)", text, re.DOTALL | re.IGNORECASE)
    if select_match2:
        return select_match2.group(1).strip()

    return None


def validate_sql(sql: str) -> bool:
    """Ensure the SQL is a SELECT query only (no modifications)."""
    normalized = sql.strip().upper()
    # Must start with SELECT or WITH (for CTEs)
    if not (normalized.startswith("SELECT") or normalized.startswith("WITH")):
        return False
    # Must NOT contain dangerous keywords
    dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE"]
    for keyword in dangerous:
        # Check for keyword as a whole word (not part of column names)
        if re.search(rf"\b{keyword}\b", normalized):
            return False
    return True


async def execute_sql_via_laravel(sql: str) -> dict:
    """Send the SQL query to the Laravel backend for execution."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                f"{LARAVEL_API_URL}/ai/query",
                json={"sql": sql},
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Laravel API error: {e.response.status_code} - {e.response.text}")
            return {"error": f"Database query failed: {e.response.text}"}
        except httpx.ConnectError:
            logger.error("Cannot connect to Laravel backend")
            return {"error": "Cannot connect to the database service. Is Laravel running?"}


def generate_sql_prompt(user_question: str) -> str:
    """Build the prompt for SQL generation."""
    return f"""{SCHEMA_CONTEXT}

### Instructions
Given the database schema above, generate a MySQL SELECT query to answer the user's question.
- ONLY generate SELECT queries. Never generate INSERT, UPDATE, DELETE, DROP, or any data-modifying statement.
- Return ONLY the SQL query inside a ```sql code block.
- If the question cannot be answered with the available tables, explain why.
- Use proper MySQL syntax.
- IMPORTANT: If the question asks about categories, origins, brands, or attributes NOT stored as columns (e.g., "which car models are from Malaysia?"), do NOT guess or filter by unrelated columns. Instead, fetch ALL distinct values from the relevant column (e.g., SELECT DISTINCT model FROM parking_sessions) so the data can be analyzed afterward.
- Never assume column values you haven't seen. When in doubt, fetch broad data rather than filtering incorrectly.

### User Question
{user_question}

### SQL Query
"""


def generate_answer_prompt(user_question: str, sql: str, result: dict) -> str:
    """Build the prompt for natural language answer generation."""
    result_str = json.dumps(result.get("data", []), indent=2, default=str)

    return f"""You are a helpful parking management assistant. The user asked a question, and a SQL query was run against the database.

### User Question
{user_question}

### SQL Query Executed
```sql
{sql}
```

### Query Result
```json
{result_str}
```

### Instructions
1. Answer the user's question in clear, natural language based on the query result.
2. Start your response by briefly showing the SQL query you used (in a code block).
3. Then provide the answer with specific numbers from the result.
4. Keep the response concise and friendly.
5. If the result is empty, say "No data found for this query."
6. IMPORTANT: If the user's question requires knowledge beyond the database (e.g., which car brands are from a specific country, vehicle classifications, etc.), USE YOUR WORLD KNOWLEDGE to analyze and categorize the query results. For example, if the user asks "how many car models belong to Malaysia?" and the data contains model names like "Proton Saga" and "Perodua Myvi", identify those as Malaysian brands using your knowledge.
7. When applying world knowledge, clearly explain your reasoning (e.g., "Proton and Perodua are Malaysian automotive manufacturers").
"""


# ==========================================
# API ENDPOINTS
# ==========================================

@app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL_ID}


@app.post("/generate")
async def generate(request: GenerateRequest):
    """
    Main endpoint: receives chat messages, generates SQL, executes it,
    and streams back a natural language answer.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    # Get the latest user message
    user_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break

    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    logger.info(f"User question: {user_message}")

    async def stream_response():
        encoder = json.dumps

        try:
            # ---- STEP 1: Generate SQL ----
            sql_prompt = generate_sql_prompt(user_message)

            logger.info("Calling HuggingFace for SQL generation...")
            sql_completion = hf_client.chat_completion(
                model=MODEL_ID,
                messages=[
                    {"role": "system", "content": "You are a SQL expert. Generate only MySQL SELECT queries."},
                    {"role": "user", "content": sql_prompt},
                ],
                max_tokens=300,
                temperature=0.1,
            )
            sql_response = sql_completion.choices[0].message.content or ""

            logger.info(f"LLM SQL response: {sql_response}")

            sql = extract_sql(sql_response)

            if not sql:
                # LLM couldn't generate SQL — stream the raw response
                error_msg = "I couldn't generate a SQL query for that question. Could you rephrase it? "
                error_msg += f"Here's what the model said: {sql_response}"
                for word in error_msg.split(" "):
                    yield f"0:{encoder(word + ' ')}\n"
                yield f'd:{{"finishReason":"stop","usage":{{"promptTokens":0,"completionTokens":0}}}}\n'
                return

            if not validate_sql(sql):
                error_msg = "I can only run SELECT queries for safety reasons. I cannot modify any data in the database."
                for word in error_msg.split(" "):
                    yield f"0:{encoder(word + ' ')}\n"
                yield f'd:{{"finishReason":"stop","usage":{{"promptTokens":0,"completionTokens":0}}}}\n'
                return

            logger.info(f"Generated SQL: {sql}")

            # ---- STEP 2: Execute SQL via Laravel ----
            result = await execute_sql_via_laravel(sql)

            if "error" in result:
                error_msg = f"The query failed: {result['error']}"
                for word in error_msg.split(" "):
                    yield f"0:{encoder(word + ' ')}\n"
                yield f'd:{{"finishReason":"stop","usage":{{"promptTokens":0,"completionTokens":0}}}}\n'
                return

            logger.info(f"Query result: {json.dumps(result, default=str)[:200]}...")

            # ---- STEP 3: Generate natural language answer ----
            answer_prompt = generate_answer_prompt(user_message, sql, result)

            logger.info("Calling HuggingFace for answer generation...")
            answer_completion = hf_client.chat_completion(
                model=MODEL_ID,
                messages=[
                    {"role": "system", "content": "You are a helpful parking management assistant."},
                    {"role": "user", "content": answer_prompt},
                ],
                max_tokens=500,
                temperature=0.3,
            )
            answer_response = answer_completion.choices[0].message.content or ""

            logger.info(f"Answer: {answer_response[:200]}...")

            # Stream the answer word by word
            for word in answer_response.split(" "):
                yield f"0:{encoder(word + ' ')}\n"

            yield f'd:{{"finishReason":"stop","usage":{{"promptTokens":0,"completionTokens":0}}}}\n'

        except Exception as e:
            logger.error(f"Error in generate: {e}")
            error_msg = f"An error occurred: {str(e)}"
            for word in error_msg.split(" "):
                yield f"0:{encoder(word + ' ')}\n"
            yield f'd:{{"finishReason":"stop","usage":{{"promptTokens":0,"completionTokens":0}}}}\n'

    return StreamingResponse(
        stream_response(),
        media_type="text/plain; charset=utf-8",
        headers={"X-Vercel-AI-Data-Stream": "v1"},
    )
