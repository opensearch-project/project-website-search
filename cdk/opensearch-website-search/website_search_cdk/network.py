import os

from aws_cdk import aws_ec2 as ec2
from aws_cdk import Stack
from constructs import Construct
#, core as cdk)

# For consistency with other languages, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.

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


class Network(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    cidr = self.node.try_get_context("cidr")
    if cidr is None or cidr == '':
      raise ValueError("CIDR cannot be null or empty")

    # value checking for stack_prefix already done in app.py, omitting here
    stack_prefix = self.node.try_get_context("stack_prefix")

    public_subnet = ec2.SubnetConfiguration(name="public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24)
    private_subnet = ec2.SubnetConfiguration(name="private", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                                             cidr_mask=24)

    self.vpc = ec2.Vpc(self, stack_prefix + "cdk-vpc",
                       cidr=cidr,
                       max_azs=3,
                       nat_gateways=1,
                       subnet_configuration=[private_subnet, public_subnet]
                       )

    vpc_flow_logs = ec2.FlowLog(self, stack_prefix + "vpc-flow-logs",
                                resource_type=ec2.FlowLogResourceType.from_vpc(self.vpc))

    self.security_group = ec2.SecurityGroup(self, stack_prefix + "cdk-security-group",
                                            vpc=self.vpc,
                                            description="Opensearch website search domain security group",
                                            security_group_name=stack_prefix + "SecurityGroup",
                                            allow_all_outbound=True,
                                            )

    self.security_group.add_ingress_rule(prefixList, ec2.Port.tcp(22), description="SSH access to the nodes")
    self.security_group.add_ingress_rule(ec2.Peer.ipv4(self.vpc.vpc_cidr_block), ec2.Port.tcp(9300),
                                         description="Transport port for cluster formation")
    self.security_group.add_ingress_rule(ec2.Peer.ipv4(self.vpc.vpc_cidr_block), ec2.Port.tcp(9200),
                                         description="OpenSearch runs on port 9200 from VPC")
    self.security_group.add_ingress_rule(ec2.Peer.ipv4(self.vpc.vpc_cidr_block), ec2.Port.tcp(9600),
                                         description="Performance Analyzer plugin port from VPC")
    self.security_group.add_ingress_rule(ec2.Peer.ipv4(self.vpc.vpc_cidr_block), ec2.Port.tcp(5601),
                                         description="Used for accessing OpenSearch Dashboards from VPC")
    self.security_group.add_ingress_rule(ec2.Peer.ipv4(self.vpc.vpc_cidr_block), ec2.Port.tcp(22),
                                         description="SSH into private subnet using public subnet nodes")
    # TODO:  What does below all traffic ingress mean and is it required?
    self.security_group.add_ingress_rule(self.security_group, ec2.Port.all_traffic())
