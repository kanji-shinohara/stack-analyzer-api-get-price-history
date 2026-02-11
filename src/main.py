import logging
import os
import json
from datetime import datetime, timedelta, timezone
from google.cloud import bigquery
import functions_framework

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT")
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

    # CORS Headers
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600",
        }
        return ("", 204, headers)

    headers = {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json"
    }

    try:
        # 1. Parse Input
        stock_code = request.args.get("code")
        days_str = request.args.get("days", "90")

        if not stock_code:
            return (json.dumps({"error": "Missing 'code' parameter"}), 400, headers)

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

        return (json.dumps({"data": data, "code": stock_code}), 200, headers)

    except Exception as e:
        logger.error(f"Error fetching price history: {e}")
        return (json.dumps({"error": str(e)}), 500, headers)
