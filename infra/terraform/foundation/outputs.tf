output "dvc_bucket_name" { value = aws_s3_bucket.dvc.id }
output "ecr_repository_url" { value = aws_ecr_repository.api.repository_url }
output "github_actions_role_arn" { value = aws_iam_role.github_actions.arn }
output "github_deploy_role_arn" { value = aws_iam_role.github_actions.arn }
