terraform {
  backend "gcs" {
    bucket = "stack-analyzer-tfstate"
    prefix = "api/stack-analyzer-api-get-price-history"
  }
}
