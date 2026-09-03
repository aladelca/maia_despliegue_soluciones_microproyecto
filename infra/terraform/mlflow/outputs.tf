output "instance_id" { value = aws_instance.mlflow_experiment.id }
output "public_ip" { value = aws_instance.mlflow_experiment.public_ip }
output "mlflow_url" {
  description = "MLflow URL while the EC2 instance has an assigned public IP; null when stopped."
  value = (
    aws_instance.mlflow_experiment.public_ip != ""
    ? "http://${aws_instance.mlflow_experiment.public_ip}:5000"
    : null
  )
}
output "artifact_bucket_name" { value = aws_s3_bucket.mlflow.id }
output "experiment_log_command" {
  value = "aws ssm start-session --target ${aws_instance.mlflow_experiment.id} --document-name AWS-StartInteractiveCommand --parameters command='sudo tail -f /var/log/online-shoppers-bootstrap.log'"
}
