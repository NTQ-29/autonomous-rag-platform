# 1. Define AWS Provider Requirements
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1" # You can swap this to us-east-2 or us-west-2 (Virginia / Arizona) later
}

# 2. Raw Document Landing Zone (Standard S3 Bucket)
resource "aws_s3_bucket" "document_landing_zone" {
  bucket        = "autonomous-rag-document-landing-ntq29"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "landing_zone_privacy" {
  bucket = aws_s3_bucket.document_landing_zone.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 3. Production Vector Store (Amazon S3 Vector Bucket & Index)
# This leverages the native AWS S3 Vector storage layer we discussed
resource "aws_s3_bucket" "vector_storage_bucket" {
  bucket        = "autonomous-rag-vector-storage-ntq29"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "vector_privacy" {
  bucket = aws_s3_bucket.vector_storage_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 4. IAM Execution Role for our LangGraph/MCP Server Application
resource "aws_iam_role" "mcp_execution_role" {
  name = "autonomous-rag-mcp-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = ["ecs-tasks.amazonaws.com", "lambda.amazonaws.com"]
        }
      }
    ]
  })
}

# Least-Privilege IAM Security Policy
resource "aws_iam_policy" "s3_vector_access_policy" {
  name        = "autonomous-rag-s3-vector-access"
  description = "Allows the MCP server to read raw docs and write/query the S3 Vector bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.document_landing_zone.arn,
          "${aws_s3_bucket.document_landing_zone.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:QueryVectorIndex" # Native AWS API permission for vector querying
        ]
        Resource = [
          aws_s3_bucket.vector_storage_bucket.arn,
          "${aws_s3_bucket.vector_storage_bucket.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_s3_access" {
  role       = aws_iam_role.mcp_execution_role.name
  policy_arn = aws_iam_policy.s3_vector_access_policy.arn
}

# 5. Infrastructure Outputs
output "landing_bucket_name" {
  value       = aws_s3_bucket.document_landing_zone.id
  description = "The target bucket for uploading raw documents."
}

output "vector_bucket_name" {
  value       = aws_s3_bucket.vector_storage_bucket.id
  description = "The target bucket where S3 Vector indexes are managed."
}
