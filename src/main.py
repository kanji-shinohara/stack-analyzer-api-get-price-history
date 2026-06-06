import logging
import os
import json
import re
from datetime import datetime, timedelta, timezone
from google.cloud import bigquery
import google.auth
import google.auth.transport.requests
import google.oauth2.id_token
import functions_framework
import firebase_admin
from firebase_admin import auth

# Initialize Firebase Admin SDK
try:
    firebase_admin.initialize_app()
except ValueError:
    pass


def get_project_id() -> str:
    project_id = (
        os.environ.get("GOOGLE_CLOUD_PROJECT") or
        os.environ.get("GCP_PROJECT") or
        os.environ.get("GCP_PROJECT_ID") or
        os.environ.get("PROJECT_ID")
    )
    if project_id:
        return project_id
    try:
        _, project_id = google.auth.default()
        if project_id:
            return project_id
    except Exception:
        pass
    return ""

# --- Configuration ---
PROJECT_ID = get_project_id()
DATASET_ID = os.environ.get("BIGQUERY_DATASET", "stack_analyzer")
TABLE_NAME = "t_daily_price"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# BigQuery Client (Lazy Init)
bq_client = None

def get_bq_client():
    global bq_client
    if bq_client is None:
        bq_client = bigquery.Client(project=PROJECT_ID)
    return bq_client

ALLOWED_ORIGIN_PATTERNS = [
    r"^http://localhost(:\d+)?$",
    r"^https://stack-analyzer-system\.web\.app$",
    r"^https://stack-analyzer-system\.firebaseapp\.com$"
]

def get_cors_headers(request):
    origin = request.headers.get("Origin")
    allowed = False
    if origin:
        for pattern in ALLOWED_ORIGIN_PATTERNS:
            if re.match(pattern, origin):
                allowed = True
                break
        if not allowed and PROJECT_ID:
            if origin == f"https://{PROJECT_ID}.web.app" or origin == f"https://{PROJECT_ID}.firebaseapp.com":
                allowed = True

    allow_origin = origin if allowed else "http://localhost:5173"
    return {
        "Access-Control-Allow-Origin": allow_origin,
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Max-Age": "3600"
    }

def verify_firebase_auth(request):
    disable_auth = os.environ.get("DISABLE_AUTH") == "true"
    if get_project_id() == "stack-analyzer-system":
        disable_auth = False

    if disable_auth:
        return {"uid": "local-dev-user", "email": "dev@example.com"}

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise Exception("Missing or invalid Authorization header. Expected Bearer <ID_TOKEN>.")

    id_token_str = auth_header.split("Bearer ")[1]
    
    try:
        decoded_token = auth.verify_id_token(id_token_str)
        return decoded_token
    except Exception as e:
        raise Exception(f"Firebase token verification failed: {e}")

@functions_framework.http
def handler(request):
    """
    Cloud Function to fetch stock price history from BigQuery.

    Query Parameters:
    - code (required): Stock code (e.g., "5208")
    - days (optional): Number of days to fetch (default: 90)

    Returns:
    - JSON list of {date, close, volume}
    """
    cors_headers = get_cors_headers(request)

    # CORS Headers
    if request.method == "OPTIONS":
        return ("", 204, cors_headers)

    # Auth verification
    try:
        verify_firebase_auth(request)
    except Exception as e:
        logger.warning(f"Unauthorized request: {e}")
        return ({"error": str(e)}, 401, cors_headers)

    headers = cors_headers

    try:
        # 1. Parse Input
        stock_code = request.args.get("code")
        days_str = request.args.get("days", "90")

        if not stock_code:
            return ({"error": "Missing 'code' parameter"}, 400, headers)

        try:
            days = int(days_str)
        except ValueError:
            days = 90

        # 2. Build Query
        # Minimal columns for chart optimization
        query = f"""
            SELECT
                date,
                close_price,
                volume
            FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_NAME}`
            WHERE stock_code = @stock_code
              AND date >= DATE_SUB(CURRENT_DATE("Asia/Tokyo"), INTERVAL @days DAY)
            ORDER BY date ASC
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("stock_code", "STRING", stock_code),
                bigquery.ScalarQueryParameter("days", "INT64", days)
            ]
        )

        # 3. Execute Query
        client = get_bq_client()
        query_job = client.query(query, job_config=job_config)
        results = query_job.result()

        # 4. Format Response
        data = []
        for row in results:
            data.append({
                "date": row.date.isoformat(),
                "close": float(row.close_price) if row.close_price is not None else None,
                "volume": int(row.volume) if row.volume is not None else 0
            })

        return ({"data": data, "code": stock_code}, 200, headers)

    except Exception as e:
        logger.error(f"Error fetching price history: {e}")
        return ({"error": str(e)}, 500, headers)
