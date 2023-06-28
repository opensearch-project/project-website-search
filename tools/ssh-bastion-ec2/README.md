Python CLI to access opensearch cluster nodes (data, master etc) via bastion hosts.
The data nodes are inside a private subnet(thus no public IP address by default). They can be ssh-ed via public facing bastion hosts with access to a restricted CIDR (generally a corp network). The CLI retrieves a random bastion IP based on tags and SSH directly to opensearch hosts via bastions.

### Prerequisites

- AWS user with credentials : You can configure the credentials using `aws` CLI or export them directly

```
#1
aws configure

# generates ~/aws/config
# generates ~/aws/credentials
```

```
#2
export AWS_ACCESS_KEY_ID=123456789101112
export AWS_SECRET_ACCESS_KEY=myexamplesecretkey
export AWS_DEFAULT_REGION=us-east-1
```

- User should have following permissions

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "<Resource ARN>"
        }
    ]
}
```
- Command dependencies : The command needs the following python dependencies 
```
Python                                >3.8
boto3                                 >1.18.38
botocore                              >1.21.38

```

### Usage

```
./ssh-bastion-ec2  --help
usage: ssh-bastion-ec2 [-h] [-s SECRET_NAME] [-k LOCAL_KEY_PATH] [-u USER] [-tn TAG_NAME] [-tv TAG_VALUE] remote_host

SSH to a OpenSearch EC2 host

positional arguments:
  remote_host           Host name or private IP address for the EC2 instance

optional arguments:
  -h, --help            show this help message and exit
  -s SECRET_NAME, --secret-name SECRET_NAME
                        Name of secret name to retrieve from AWS Secrets Manager
  -k LOCAL_KEY_PATH, --key-path LOCAL_KEY_PATH
                        File path to local private key
  -u USER, --user USER  User to login, same for both bastion and remote host
  -tn TAG_NAME, --tag-name TAG_NAME
                        Tag name to discover EC2 bastion hosts
  -tv TAG_VALUE, --tag-value TAG_VALUE
                        Tag value to discover EC2 bastion hosts for give tag name
```

```
# Defaults

USER: ec2-user
TAG_NAME: role
TAG_VALUE: opensearch-bastion-hosts
```

Example commands

1. ssh to nodes using private key stored in AWS Secrets Manager

```
./ssh-bastion-ec2  -s "prod/opensearch/myPrivateKey" 10.9.1.123
```

2. ssh to nodes using private key available locally by defining its path. The path can be absolute name or key file present in current working directory. 

```
./ssh-bastion-ec2 -tn role -tv us-east-1-opensearch-bastion-hosts -k "/Users/abbashus/<private-key-name>.cer" 10.9.1.123 
```
 
 
