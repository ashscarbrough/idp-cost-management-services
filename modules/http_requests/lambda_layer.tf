resource "aws_lambda_layer_version" "requests_layer" {
  layer_name =  "python313-requests-layer"
  filename   = "${path.module}/requests/requests_layer.zip"
  source_code_hash = filebase64sha256("${path.module}/requests/requests_layer.zip")

  compatible_runtimes = ["python3.13"]
}
