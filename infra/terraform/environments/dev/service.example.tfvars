owner          = "replace-me"
image_uri      = "123456789012.dkr.ecr.us-east-1.amazonaws.com/online-shoppers-ml-api@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
allowed_origin = "https://replace-me.vercel.app"

# Set this to the existing LabRole ARN in voclabs. Leave null in an account
# where Terraform is allowed to create a dedicated Lambda execution role.
lambda_execution_role_arn = null
