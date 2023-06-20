#!/usr/bin/env python3
import os

from aws_cdk import App, Environment
from aws_cdk import aws_ec2 as ec2
from website_search_cdk.network import Network
from website_search_cdk.api_lambda import ApiLambdaStack
from website_search_cdk.monitoring import MonitoringStack
from website_search_cdk.alarms import AlarmsStack
from website_search_cdk.bastions import Bastions

from website_search_cdk.infra import Architecture, Security, ClusterStack

from opensearch_website_search.opensearch_website_search_stack import OpensearchWebsiteSearchStack

env = Environment(account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
                  region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]))

app = App()
OpensearchWebsiteSearchStack(app, "OpensearchWebsiteSearch2Stack",
                             # If you don't specify 'env', this stack will be environment-agnostic.
                             # Account/Region-dependent features and context lookups will not work,
                             # but a single synthesized template can be deployed anywhere.

                             # Uncomment the next line to specialize this stack for the AWS Account
                             # and Region that are implied by the current CLI configuration.

                             env=Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),

                             # Uncomment the next line if you know exactly what Account and Region you
                             # want to deploy the stack to. */

                             #env=cdk.Environment(account='123456789012', region='us-east-1'),

                             # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
                             )

stack_prefix = app.node.try_get_context("stack_prefix")
if not stack_prefix:
    raise ValueError(stack_prefix, "is either null or empty. Please use a prefix to differentiate"
                                   " between stack and prevent from overriding other stacks")

architecture = app.node.try_get_context("architecture")
if not (Architecture.has_value(architecture)):
    raise ValueError(architecture, "is either null or not supported yet! Please use either x64 or arm64")

security = app.node.try_get_context("security")
if not (Security.has_security_value(security)):
    raise ValueError(security, "The keyword has to be either of these two: enable or disable.")

cluster_stack_name = app.node.try_get_context("cluster_stack_name")
network_stack_name = app.node.try_get_context("network_stack_name")
search_access_stack_name = app.node.try_get_context("search_access_stack_name")
monitoring_stack_name = app.node.try_get_context("monitoring_stack_name")

if not cluster_stack_name:
    raise ValueError(" Cluster stack name cannot be None. Please provide the right stack name")
if not network_stack_name:
    raise ValueError(" Network stack name cannot be None. Please provide the right stack name")

network = Network(app, stack_prefix + network_stack_name,
                  # If you don't specify 'env', this stack will be environment-agnostic.
                  # Account/Region-dependent features and context lookups will not work,
                  # but a single synthesized template can be deployed anywhere.

                  # Uncomment the next line to specialize this stack for the AWS Account
                  # and Region that are implied by the current CLI configuration.

                  # env=core.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'),
                  #                      region=os.getenv('CDK_DEFAULT_REGION')),

                  # Uncomment the next line if you know exactly what Account and Region you
                  # want to deploy the stack to. */

                  # env=core.Environment(account='123456789012', region='us-east-1'),

                  # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
                  env=env,
                  )
opensearch_infra = ClusterStack(app, stack_prefix + cluster_stack_name, vpc=network.vpc, sg=network.security_group,
                                architecture=architecture, security=security, env=env)

api_lambda = ApiLambdaStack(app, stack_prefix + search_access_stack_name, network.vpc, opensearch_infra.nlb,
                            opensearch_infra.opensearch_listener, env=env)
monitoring = MonitoringStack(app, stack_prefix + monitoring_stack_name, network.vpc, opensearch_infra.nlb, env=env)
alarms = AlarmsStack(app, stack_prefix + "alarms", env=env)
bastion_host_infra = Bastions(app, stack_prefix + 'bastion-hosts', network.vpc, env=env)

app.synth()
