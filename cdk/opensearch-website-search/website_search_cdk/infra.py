import datetime
from enum import Enum

from aws_cdk import (aws_autoscaling as asg, aws_ec2 as ec2, aws_elasticloadbalancingv2 as elb, aws_iam as iam,
                     aws_logs as logs, core as cdk)
from aws_cdk.core import Tags


# For consistency with other languages, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.

# Refer: https://github.com/aws/aws-cdk/blob/master/packages/%40aws-cdk/aws-ec2/lib/instance-types.ts
class InstanceClass(Enum):
  m3 = ec2.InstanceClass.STANDARD3
  m4 = ec2.InstanceClass.STANDARD4
  m5 = ec2.InstanceClass.STANDARD5
  m6g = ec2.InstanceClass.STANDARD6_GRAVITON


class Architecture(Enum):
  X64 = "x64"
  ARM64 = "arm64"

  @classmethod
  def has_value(cls, value):
    return value in cls._value2member_map_


class Security(Enum):
  ENABLE = "enable"
  DISABLE = "disable"

  @classmethod
  def has_security_value(cls, value):
    return value in cls._value2member_map_


class ClusterStack(cdk.Stack):
  def __init__(self, scope: cdk.Construct, construct_id: str, vpc, sg, architecture, security, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    # Context variables can be passed from command line using -c/--context flag. The values are stored in
    # cdk.context.json file. If you do not pass any command line context key values,
    # the defaults will be picked up from cdk.context.json file
    distribution = self.node.try_get_context("distribution")
    url = self.node.try_get_context("url")
    dashboards_url = self.node.try_get_context("dashboards_url")

    # value checking for stack_prefix already done in app.py, omitting here
    stack_prefix = self.node.try_get_context("stack_prefix")

    # TODO: add value checks for master_node_count, data_node_count and data_node_count
    master_node_count = int(self.node.try_get_context("master_node_count"))
    data_node_count = int(self.node.try_get_context("data_node_count"))

    keypair = self.node.try_get_context("keypair")
    if keypair is None or keypair == '':
      raise ValueError("Please provide the EC2 keypair")
    if url is None or url == '':
      raise ValueError("url cannot be null or empty")
    if dashboards_url is None or dashboards_url == '':
      raise ValueError(" dashboard_url cannot be null or empty")
    if distribution is None or distribution == '' or distribution != "tar":
      raise ValueError("Distribution cannot be null or empty. Please use tar ")

    nlb_opensearch_port = int(self.node.try_get_context("nlb_opensearch_port")) or 80
    nlb_dashboards_port = int(self.node.try_get_context("nlb_dashboards_port")) or 5601

    # ami_id = self.node.try_get_context("ami_id")
    # if ami_id is None or ami_id == '':
    #   raise ValueError("Please provide a valid ami-id. This should be a Amazon Linux 2 based AMI")

    ami_id = ec2.MachineImage.latest_amazon_linux(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
                                                  cpu_type=ec2.AmazonLinuxCpuType.X86_64)

    # Creating IAM role for read only access
    read_secrets_policy = iam.PolicyStatement(
      effect=iam.Effect.ALLOW,
      actions=["secretsmanager:GetResourcePolicy",
               "secretsmanager:GetSecretValue",
               "secretsmanager:DescribeSecret",
               "secretsmanager:ListSecretVersionIds",
               "secretsmanager:GetRandomPassword",
               "secretsmanager:ListSecrets"
               ],
      resources=["arn:aws:secretsmanager:*:*:secret:*"],
    )
    read_secrets_document = iam.PolicyDocument()
    read_secrets_document.add_statements(read_secrets_policy)

    ec2_iam_role = iam.Role(self, "ec2_iam_role",
                            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
                            managed_policies=[
                              iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ReadOnlyAccess"),
                              iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchAgentServerPolicy")
                            ],
                            inline_policies={'ReadSecrets': read_secrets_document}
                            )

    # def get_ec2_settings(arch):
    #     if arch == Architecture.X64.value:
    #         instance_type = ec2.InstanceType.of(InstanceClass.m5.value, ec2.InstanceSize.XLARGE)
    #         ami_id = ec2.MachineImage.latest_amazon_linux(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
    #                                                       cpu_type=ec2.AmazonLinuxCpuType.X86_64)
    #         return instance_type, ami_id
    #     elif arch == Architecture.ARM64.value:
    #         instance_type = ec2.InstanceType.of(InstanceClass.m6g.value, ec2.InstanceSize.XLARGE)
    #         ami_id = ec2.MachineImage.latest_amazon_linux(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
    #                                                       cpu_type=ec2.AmazonLinuxCpuType.ARM_64)
    #         return instance_type, ami_id
    #     else:
    #         raise ValueError("Unrecognised architecture")

    stack_name = cdk.Stack.of(self).stack_name

    # Logging
    dt = datetime.datetime.utcnow()
    dtformat = dt.strftime("%m-%d-%y-t%H-%M")
    lg = logs.LogGroup(self, "LogGroup",
                       log_group_name=stack_name + '-' + dtformat,
                       retention=logs.RetentionDays.THREE_MONTHS)

    # Creating userdata for installation process
    log_group_name = lg.log_group_name
    userdata_map = {
      "common": {
        "__URL__": url,
        "__STACK_NAME__": stack_name,
        "__LG__": log_group_name,
        "__SECURITY_PARAM__": security
      },
      "master": {
        "__NODE_NAME__": "__MASTER__",
        "__MASTER__": "true",
        "__DATA__": "false",
        "__INGEST__": "false"
      },
      "seed": {
        "__NODE_NAME__": "seed",
        "__MASTER__": "true",
        "__DATA__": "true",
        "__INGEST__": "false"
      },
      "data": {
        "__NODE_NAME__": "data-node",
        "__MASTER__": "false",
        "__DATA__": "true",
        "__INGEST__": "true"
      },
      "client": {
        "__NODE_NAME__": "client-node",
        "__MASTER__": "false",
        "__DATA__": "false",
        "__INGEST__": "false"
      },
      "dashboards": {
        "__DASHBOARDS_URL__": dashboards_url,
        "__SECURITY_PARAM__": security
      }
    }
    userdata_map["master"].update(userdata_map["common"])
    userdata_map["client"].update(userdata_map["common"])
    userdata_map["seed"].update(userdata_map["common"])
    userdata_map["data"].update(userdata_map["common"])

    with open(f"./userdata/{distribution}/main.sh") as f:
      master_userdata = cdk.Fn.sub(f.read(), userdata_map["master"])
    with open(f"./userdata/{distribution}/main.sh") as f:
      seed_userdata = cdk.Fn.sub(f.read(), userdata_map["seed"])
    with open(f"./userdata/{distribution}/main.sh") as f:
      data_userdata = cdk.Fn.sub(f.read(), userdata_map["data"])
    with open(f"./userdata/{distribution}/main.sh") as f:
      client_userdata = cdk.Fn.sub(f.read(), userdata_map["client"])
    with open(f"./userdata/{distribution}/dashboards.sh") as f:
      dashboards_userdata = cdk.Fn.sub(f.read(), userdata_map["dashboards"])

    # # ec2_instance_type, ami_id = get_ec2_settings(architecture)
    # ami_id = ec2.MachineImage.latest_amazon_linux(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
    #                                               cpu_type=ec2.AmazonLinuxCpuType.X86_64)

    # Launching autoscaling groups that will configure all nodes
    master_nodes = asg.AutoScalingGroup(self, "MasterASG",
                                        instance_type=ec2.InstanceType.of(InstanceClass.m5.value,
                                                                          ec2.InstanceSize.XLARGE),
                                        machine_image=ami_id,
                                        vpc=vpc, security_group=sg,
                                        desired_capacity=master_node_count,
                                        max_capacity=master_node_count,
                                        min_capacity=master_node_count,
                                        vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE),
                                        key_name=keypair,
                                        # TODO: do we still need to have keypair since this will be in private subnet
                                        role=ec2_iam_role,
                                        user_data=ec2.UserData.custom(master_userdata))
    Tags.of(master_nodes).add("role", "master")

    # TODO: Can the seed ASG be eliminated?
    seed_node = asg.AutoScalingGroup(self, "SeedASG",
                                     instance_type=ec2.InstanceType.of(InstanceClass.m5.value, ec2.InstanceSize.XLARGE),
                                     machine_image=ami_id,
                                     vpc=vpc, security_group=sg,
                                     desired_capacity=1,
                                     max_capacity=1,
                                     min_capacity=1,
                                     vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE),
                                     key_name=keypair,
                                     # TODO: do we still need to have keypair since this will be in private subnet
                                     role=ec2_iam_role,
                                     user_data=ec2.UserData.custom(seed_userdata))
    Tags.of(seed_node).add("role", "master")

    # Data nodes should be equally spread across 3 AZ's to resist AZ outages
    data_nodes = asg.AutoScalingGroup(self, "DataASG",
                                      instance_type=ec2.InstanceType.of(InstanceClass.m5.value,
                                                                        ec2.InstanceSize.XLARGE),
                                      machine_image=ami_id,
                                      vpc=vpc, security_group=sg,
                                      desired_capacity=data_node_count,
                                      max_capacity=data_node_count,
                                      min_capacity=data_node_count,
                                      vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE),
                                      key_name=keypair,
                                      # TODO: do we still need to have keypair since this will be in private subnet
                                      role=ec2_iam_role,
                                      user_data=ec2.UserData.custom(data_userdata + dashboards_userdata))
    Tags.of(data_nodes).add("role", "data")

    # creating an private network load balancer to have a single endpoint
    # TODO: enable logging, requires configuring a S3 bucket
    self.nlb = elb.NetworkLoadBalancer(self, stack_prefix + "NetworkLoadBalancer",
                                       vpc=vpc,
                                       internet_facing=False,
                                       vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE))

    self.opensearch_listener = self.nlb.add_listener("opensearch", port=nlb_opensearch_port,
                                                     protocol=elb.Protocol.TCP)
    self.dashboards_listener = self.nlb.add_listener("dashboards", port=nlb_dashboards_port,
                                                     protocol=elb.Protocol.TCP)

    # Default Port mapping
    # 80 : 9200 OpenSearch
    # 5601 : 5601 OpenSearch-Dashboards
    self.opensearch_listener.add_targets("OpenSearchTarget",
                                         port=9200,
                                         targets=[data_nodes])
    self.dashboards_listener.add_targets("DashboardsTarget",
                                         port=5601,
                                         targets=[data_nodes])
    cdk.CfnOutput(self, "Load Balancer Endpoint",
                  value=self.nlb.load_balancer_dns_name)
