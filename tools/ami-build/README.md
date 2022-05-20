This directory includes configuration and other files needed by [HashiCorp Packer](https://packer.io) to create AMIs (Amazon Machine Image). Packer config files are written in HCL (a domain specific language).

Packer is an open source utility designed to automate the creation of identical virtual machine images for multiple platforms from a single source configuration.

### Prerequisites

- Packer: See [installation instructions here](https://learn.hashicorp.com/tutorials/packer/get-started-install-cli?in=packer/aws-get-started).

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

- User should have following [permissions](https://www.packer.io/docs/builders/amazon#iam-task-or-instance-role).  

```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:AttachVolume",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:CopyImage",
        "ec2:CreateImage",
        "ec2:CreateKeypair",
        "ec2:CreateSecurityGroup",
        "ec2:CreateSnapshot",
        "ec2:CreateTags",
        "ec2:CreateVolume",
        "ec2:DeleteKeyPair",
        "ec2:DeleteSecurityGroup",
        "ec2:DeleteSnapshot",
        "ec2:DeleteVolume",
        "ec2:DeregisterImage",
        "ec2:DescribeImageAttribute",
        "ec2:DescribeImages",
        "ec2:DescribeInstances",
        "ec2:DescribeInstanceStatus",
        "ec2:DescribeRegions",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeSnapshots",
        "ec2:DescribeSubnets",
        "ec2:DescribeTags",
        "ec2:DescribeVolumes",
        "ec2:DetachVolume",
        "ec2:GetPasswordData",
        "ec2:ModifyImageAttribute",
        "ec2:ModifyInstanceAttribute",
        "ec2:ModifySnapshotAttribute",
        "ec2:RegisterImage",
        "ec2:RunInstances",
        "ec2:StopInstances",
        "ec2:TerminateInstances"
      ],
      "Resource": "*"
    }
  ]
}

```

### Usage

- Format HCL config files:

```
# Formats all files in current directory
packer fmt .

# Formats a specific file in current directory
packer fmt opensearch-amazon-linux.pkr.hcl
```

- Validate:


```
# Validates all files in current directory
packer validate .

# Validates a specific file in current directory
packer validate opensearch-amazon-linux.pkr.hcl
```

- Build AMI:

```
packer build opensearch-amazon-linux.pkr.hcl
```

- All available options:

```
packer --help
Usage: packer [--version] [--help] <command> [<args>]

Available commands are:
    build           build image(s) from template
    console         creates a console for testing variable interpolation
    fix             fixes templates from old versions of packer
    fmt             Rewrites HCL2 config files to canonical format
    hcl2_upgrade    transform a JSON template into an HCL2 configuration
    init            Install missing plugins or upgrade plugins
    inspect         see components of a template
    validate        check that a template is valid
    version         Prints the Packer version

```