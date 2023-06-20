from aws_cdk import Stack, Duration
from aws_cdk import aws_cloudwatch as cloudwatch
from constructs import Construct


class AlarmsStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    alarm_name_template = f'[{self.region}][website-search]{{}}'
    ONE_MINUTE_DURATION = Duration.minutes(1)
    NAMESPACE = 'opensearch-website-search'

    alarms = [
      {
        "alarm_name": alarm_name_template.format("master-not-reachable"),
        "alarm_description": "Master is not reachable for opensearch.org website search OpenSearch cluster.",
        "metric_namespace": NAMESPACE,
        "metric_name": "MasterReachableFromNLB",
        "period": ONE_MINUTE_DURATION,
        "threshold": 1,
        "comparison_operator": cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
        "evaluation_periods": 3,
        "datapoints_to_alarm": 3,
        "treat_missing_data": cloudwatch.TreatMissingData.BREACHING
      },
      {
        "alarm_name": alarm_name_template.format("red-cluster"),
        "alarm_description": "One or more indices are missing primary shard.",
        "metric_namespace": NAMESPACE,
        "metric_name": "ClusterStatus.red",
        "period": ONE_MINUTE_DURATION,
        "threshold": 0,
        "comparison_operator": cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        "evaluation_periods": 3,
        "datapoints_to_alarm": 3,
        "treat_missing_data": cloudwatch.TreatMissingData.BREACHING
      },
      {
        "alarm_name": alarm_name_template.format("unassigned-shards"),
        "alarm_description": "Some shards are unassigned",
        "metric_namespace": NAMESPACE,
        "metric_name": "Shards.unassignedShards",
        "period": ONE_MINUTE_DURATION,
        "threshold": 0,
        "comparison_operator": cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        "evaluation_periods": 3,
        "datapoints_to_alarm": 3,
        "treat_missing_data": cloudwatch.TreatMissingData.BREACHING
      },
      {
        "alarm_name": alarm_name_template.format("monitoring-failed"),
        "alarm_description": "The monitoring Lambda function is not working as expected.",
        "metric_namespace": NAMESPACE,
        "metric_name": "ClusterHealth.Failed",
        "period": ONE_MINUTE_DURATION,
        "threshold": 0,
        "comparison_operator": cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        "evaluation_periods": 3,
        "datapoints_to_alarm": 3,
        "treat_missing_data": cloudwatch.TreatMissingData.BREACHING
      }
    ]

    for alarm in alarms:
      cs_alarm = cloudwatch.Alarm(self, alarm.get('alarm_name') + '-alarm',
                                  alarm_name=alarm.get('alarm_name'),
                                  alarm_description=alarm.get('alarm_description'),
                                  metric=cloudwatch.Metric(namespace=alarm.get('metric_namespace'),
                                                           metric_name=alarm.get('metric_name'),
                                                           period=alarm.get('period', ONE_MINUTE_DURATION)),
                                  threshold=alarm.get('threshold'),
                                  comparison_operator=alarm.get('comparison_operator'),
                                  evaluation_periods=alarm.get('evaluation_periods', 3),
                                  datapoints_to_alarm=alarm.get('datapoints_to_alarm', 3),
                                  treat_missing_data=alarm.get('treat_missing_data', cloudwatch.TreatMissingData.BREACHING)
                                  )
