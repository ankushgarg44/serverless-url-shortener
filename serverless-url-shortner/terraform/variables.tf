variable "region" {
  description = "AWS region in which to deploy the application."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name used to prefix AWS resources."
  type        = string
  default     = "portfolio-url-shortener"

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "project_name may contain only lowercase letters, numbers, and hyphens."
  }
}

variable "shortener_table" {
  description = "DynamoDB table used to store short URL mappings."
  type        = string
  default     = "url-shortener-table"
}

variable "throttling_rate_limit" {
  description = "Steady-state requests per second allowed by API Gateway."
  type        = number
  default     = 10
}

variable "throttling_burst_limit" {
  description = "Maximum API Gateway request burst."
  type        = number
  default     = 20
}
