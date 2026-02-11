variable "project_id" {
  description = "The ID of the project in which to provision resources."
  type        = string
}

variable "project_region" {
  description = "The region in which to provision resources."
  type        = string
  default     = "asia-northeast1"
}

variable "bucket_name" {
  description = "The name of the GCS bucket to store the function code."
  type        = string
}
