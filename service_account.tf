resource "google_service_account" "api_get_price_history" {
  account_id   = "api-get-price-history-sa"
  display_name = "Service Account for api-get-price-history"
  project      = var.project_id
}

resource "google_project_iam_member" "api_get_price_history_bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.api_get_price_history.email}"
}

resource "google_project_iam_member" "api_get_price_history_bigquery_data_viewer" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.api_get_price_history.email}"
}

resource "google_project_iam_member" "api_get_price_history_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.api_get_price_history.email}"
}
