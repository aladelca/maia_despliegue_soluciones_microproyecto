output "dvc_bucket_name" { value = aws_s3_bucket.dvc.id }
output "ecr_repository_url" { value = try(aws_ecr_repository.api[0].repository_url, null) }
output "github_actions_role_arn" { value = try(aws_iam_role.github_actions[0].arn, null) }
output "github_deploy_role_arn" { value = try(aws_iam_role.github_actions[0].arn, null) }
