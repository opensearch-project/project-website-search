import os

from aws_cdk import aws_autoscaling as asg
from aws_cdk import aws_ec2 as ec2
from constructs import Construct
from aws_cdk import Tags, Stack

# These are corp only access prefixes per region (you can access resources only within amazon corp network)
# More info: https://apll.corp.amazon.com/
REGION_PREFIX_MAP = {
  "ap-northeast-1": "pl-bea742d7",
  "ap-northeast-2": "pl-8fa742e6",
  "ap-northeast-3": "pl-42a6432b",
  "ap-south-1": "pl-f0a04599",
  "ap-southeast-1": "pl-60a74209",
  "ap-southeast-2": "pl-04a7426d",
  "ca-central-1": "pl-85a742ec",
  "eu-central-1": "pl-19a74270",
  "eu-north-1": "pl-c2aa4fab",
  "eu-west-1": "pl-01a74268",
  "eu-west-2": "pl-fca24795",
  "eu-west-3": "pl-7dac4914",
  "sa-east-1": "pl-a6a742cf",
  "us-east-1": "pl-60b85b09",
  "us-east-2": "pl-3ea44157",
  "us-west-1": "pl-a4a742cd",
  "us-west-2": "pl-f8a64391"
}
region = os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"])
prefixList = ec2.Peer.prefix_list(REGION_PREFIX_MAP[region])


class Bastions(Stack):

  def __init__(self, scope: Construct, construct_id: str, vpc, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    stack_prefix = self.node.try_get_context("stack_prefix")
    keypair = self.node.try_get_context("keypair")
    capacity = 3  # One in each AZ

    if keypair is None or keypair == '':
      raise ValueError("Please provide the EC2 keypair")

    # t3.micro CPU:2 Mem:2GiB $0.0104
    instance_type = ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO)
    ami_id = ec2.MachineImage.latest_amazon_linux(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
                                                  cpu_type=ec2.AmazonLinuxCpuType.X86_64)

    bastion_security_group = ec2.SecurityGroup(self, stack_prefix + "bastion-security-group",
                                               vpc=vpc,
                                               description="Security group for bastion hosts restricted to corp CIDR",
                                               security_group_name=stack_prefix + "bastion-security-group",
                                               allow_all_outbound=True,
                                               )

    bastion_security_group.add_ingress_rule(prefixList, ec2.Port.tcp(22), description="SSH access from restricted CIDR")

    # TODO:  What does below all traffic ingress mean and is it required? Can this be more restricted?
    bastion_security_group.add_ingress_rule(bastion_security_group, ec2.Port.all_traffic())

    bastion_nodes = asg.AutoScalingGroup(self, "BastionASG",
                                         instance_type=instance_type,
                                         machine_image=ami_id,
                                         vpc=vpc, security_group=bastion_security_group,
                                         desired_capacity=capacity,
                                         max_capacity=capacity,
                                         min_capacity=capacity,
                                         vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
                                         key_name=keypair
                                         )

    Tags.of(bastion_nodes).add("role", region + "-" + "opensearch-bastion-hosts")
