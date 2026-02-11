resource "google_storage_bucket_object" "api_get_price_history_source" {
  name   = "api-get-price-history-${filesha256("src/main.py")}.zip"
  bucket = var.bucket_name
  source = data.archive_file.api_get_price_history.output_path
}

data "archive_file" "api_get_price_history" {
  type        = "zip"
  source_dir  = "src"
  output_path = "${path.module}/.terraform/tmp/api-get-price-history.zip"
}

resource "google_cloudfunctions_function" "api_get_price_history" {
  name        = "api-get-price-history"
  project     = var.project_id
  region      = var.project_region
  description = "Get stock price history from BigQuery"
  runtime     = "python311"

  available_memory_mb   = 256
  source_archive_bucket = var.bucket_name
  source_archive_object = google_storage_bucket_object.api_get_price_history_source.name
  trigger_http          = true
  entry_point           = "handler"
  timeout               = 60

  service_account_email = google_service_account.api_get_price_history.email

  environment_variables = {
    GCP_PROJECT      = var.project_id
    BIGQUERY_DATASET = "stack_analyzer"
    LOG_LEVEL        = "INFO"
  }
}

# Allow public invocation (or restricted if possible, but following pattern)
resource "google_cloudfunctions_function_iam_member" "api_get_price_history_invoker" {
  project        = google_cloudfunctions_function.api_get_price_history.project
  region         = google_cloudfunctions_function.api_get_price_history.region
  cloud_function = google_cloudfunctions_function.api_get_price_history.name

  role   = "roles/cloudfunctions.invoker"
  member = "allUsers"
}
