from aws_cdk import (aws_ec2 as ec2, aws_events as events, aws_events_targets as targets, aws_iam as iam,
                     aws_lambda as aws_lambda, core as cdk)
import os

class MonitoringStack(cdk.Stack):

  def __init__(self, scope: cdk.Construct, construct_id: str, vpc, nlb, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    monitoring_user = self.node.try_get_context("monitoring_user")
    monitoring_pass = self.node.try_get_context("monitoring_pass")

    custom_cw_metrics_policy = iam.PolicyStatement(
      effect=iam.Effect.ALLOW,
      actions=["cloudwatch:PutMetricData"],
      resources=["*"],
    )
    custom_cw_metrics_document = iam.PolicyDocument()
    custom_cw_metrics_document.add_statements(custom_cw_metrics_policy)

    monitoring_role = iam.Role(self, "monitoring_role",
                               assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                               managed_policies=[
                                 iam.ManagedPolicy.from_aws_managed_policy_name("service-role"
                                                                                "/AWSLambdaBasicExecutionRole"),
                                 iam.ManagedPolicy.from_aws_managed_policy_name("service-role"
                                                                                "/AWSLambdaVPCAccessExecutionRole"),
                               ],
                               inline_policies={'PutCustomCWMetrics': custom_cw_metrics_document}
                               )

    # TODO: Configure Lambda provisioned concurrency, requires setting alias, version etc
    monitoring_lambda = aws_lambda.Function(self, 'MonitoringLambda',
                                            handler='monitor.handler',
                                            runtime=aws_lambda.Runtime.PYTHON_3_8,
                                            code=aws_lambda.Code.asset('lambdas/monitoring-lambda'),
                                            vpc=vpc,
                                            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE),
                                            role=monitoring_role,
                                            environment={
                                              'MONITORING_USER': os.getenv("MONITORING_USER", monitoring_user),
                                              'MONITORING_PASS': os.getenv("MONITORING_PASS", monitoring_pass),
                                              'NLB_ENDPOINT': nlb.load_balancer_dns_name,
                                              'NLB_OPENSEARCH_PORT': self.node.try_get_context(
                                                "nlb_opensearch_port") or 80,
                                              'NLB_DASHBOARD_PORT': self.node.try_get_context(
                                                "nlb_dashboards_port") or 5601,
                                            })
    # Run every minute
    # See https://docs.aws.amazon.com/lambda/latest/dg/tutorial-scheduled-events-schedule-expressions.html
    rule = events.Rule(
      self, "OpenSearchMonitoringRule",
      schedule=events.Schedule.cron(
        minute='*',
        hour='*',
        month='*',
        week_day='*',
        year='*'),
    )
    rule.add_target(targets.LambdaFunction(monitoring_lambda))
