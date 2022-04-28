import json
import boto3
import logging
import requests
import os
from enum import Enum
from requests.auth import HTTPBasicAuth

# TODO: Adds redundant request ID into logs, fix logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

username = os.getenv('MONITORING_USER')
password = os.getenv('MONITORING_PASS')
nlb_endpoint = os.getenv('NLB_ENDPOINT')
nlb_opensearch_port = os.getenv('NLB_OPENSEARCH_PORT', "80")
nlb_dashboards_port = os.getenv('NLB_DASHBOARD_PORT', "5601")
opensearch_base_url = 'http://' + nlb_endpoint + ':' + nlb_opensearch_port
dashboards_base_url = 'http://' + nlb_endpoint + ':' + nlb_dashboards_port

http_basic_auth = HTTPBasicAuth(username, password)


"""
MetricData=[
    {
        'MetricName': 'string',
        'Dimensions': [
            {
                'Name': 'string',
                'Value': 'string'
            },
        ],
        'Timestamp': datetime(2015, 1, 1),
        'Value': 123.0,
        'StatisticValues': {
            'SampleCount': 123.0,
            'Sum': 123.0,
            'Minimum': 123.0,
            'Maximum': 123.0
        },
        'Values': [
            123.0,
        ],
        'Counts': [
            123.0,
        ],
        'Unit': 'Seconds'|'Microseconds'|'Milliseconds'|'Bytes'|'Kilobytes'|'Megabytes'|'Gigabytes'|'Terabytes'|'Bits'|'Kilobits'|'Megabits'|'Gigabits'|'Terabits'|'Percent'|'Count'|'Bytes/Second'|'Kilobytes/Second'|'Megabytes/Second'|'Gigabytes/Second'|'Terabytes/Second'|'Bits/Second'|'Kilobits/Second'|'Megabits/Second'|'Gigabits/Second'|'Terabits/Second'|'Count/Second'|'None',
        'StorageResolution': 123
    },
]
"""


class OpenSearchHealthStatus(Enum):
  RED = 1
  YELLOW = 2
  GREEN = 3


class ShardCountTypes(Enum):
  ACTIVE_PRIMARY_SHARDS = 1
  ACTIVE_SHARDS = 2
  DELAYED_UNASSIGNED_SHARDS = 3
  INITIALIZING_SHARDS = 4
  RELOCATING_SHARDS = 5
  UNASSIGNED_SHARDS = 6


def to_upper_camel_case(snake_str):
  components = snake_str.split('_')
  return components[0] + ''.join(x.title() for x in components[1:])


class CWMetricData():

  def __init__(self, namespace):
    self.metric_data = []
    self.namespace = namespace

  def add(self, metric):
    self.metric_data.append(metric)

  def get_all_metrics(self):
    return self.metric_data

  def get_namespace(self):
    return self.namespace


def check_cluster_health(metric_data):
  cluster_health_url = opensearch_base_url + '/_cluster/health?pretty'
  headers = {"Content-Type": "application/json"}

  STATUS_PREFIX = 'ClusterStatus.'
  SHARD_PREFIX = 'Shards.'

  try:
    res = requests.get(cluster_health_url, auth=http_basic_auth, headers=headers, verify=False)
    health = res.json()

    # check master available metric
    if "discovered_master" in health and health["discovered_master"]:
      metric_data.add({
        'MetricName': 'MasterReachableFromNLB',
        'Value': 1.0,
        'Unit': 'Count',
        'StorageResolution': 60
      })
    else:
      metric_data.add({
        'MetricName': 'MasterReachableFromNLB',
        'Value': 0.0,
        'Unit': 'Count',
        'StorageResolution': 60
      })
    logger.info("Successfully collected master metrics")

    # cluster health status metric
    if "status" in health:
      for status in OpenSearchHealthStatus:
        colored_status = status.name.lower()
        if health['status'] == colored_status:
          metric_data.add({
            'MetricName': STATUS_PREFIX + colored_status,
            'Value': 1.0,
            'Unit': 'Count',
            'StorageResolution': 60
          })
        else:
          metric_data.add({
            'MetricName': STATUS_PREFIX + colored_status,
            'Value': 0.0,
            'Unit': 'Count',
            'StorageResolution': 60
          })
    logger.info("Successfully collected cluster status metrics")

    # Add node count metric
    if "number_of_nodes" in health:
      metric_data.add({
        'MetricName': 'Nodes',
        'Value': health["number_of_nodes"],
        'Unit': 'Count',
        'StorageResolution': 60
      })
    logger.info("Successfully collected node count metric")

    # Add shard count metric
    for shard_count_type in ShardCountTypes:
      shard_type = shard_count_type.name.lower()
      if shard_type in health:
        metric_data.add({
          'MetricName': SHARD_PREFIX + to_upper_camel_case(shard_type.removeprefix("_shards")),
          'Value': health[shard_type],
          'Unit': 'Count',
          'StorageResolution': 60
        })
    logger.info("Successfully collected shard count metrics")

    # Add pending task metric
    if "number_of_pending_tasks" in health:
      metric_data.add({
        'MetricName': 'PendingTasks',
        'Value': health["number_of_pending_tasks"],
        'Unit': 'Count',
        'StorageResolution': 60
      })
    logger.info("Successfully collected pending_tasks metrics")

    metric_data.add({
      'MetricName': 'ClusterHealth.Failed',
      'Value': 0.0,
      'Unit': 'Count',
      'StorageResolution': 60
    })
    logger.info("All check_cluster_health metrics collected")

  except Exception as e:
    logger.exception(e)
    metric_data.add({
      'MetricName': 'ClusterHealth.Failed',
      'Value': 1.0,
      'Unit': 'Count',
      'StorageResolution': 60
    })


def check_dashboards_health(metric_data):
  dashboards_status_url = dashboards_base_url + '/api/status'
  val = 0.0
  try:
    res = requests.get(dashboards_status_url).json()

    if res['status']['overall']['state'] == 'green':
      val = 1.0

    metric_data.add({
      'MetricName': 'OpenSearchDashboardsHealthyNodes',
      'Value': val,
      'Unit': 'Count',
      'StorageResolution': 60
    })

    logger.info("All check_dashboards_health metrics collected")
  except Exception as e:
    logger.exception(e)
    metric_data.add({
      'MetricName': 'OpenSearchDashboardsHealthyNodes',
      'Value': 0.0,
      'Unit': 'Count',
      'StorageResolution': 60
    })


def handler(event, context):
  cw = boto3.client("cloudwatch")
  metrics = CWMetricData("opensearch-website-search")
  check_cluster_health(metrics)
  check_dashboards_health(metrics)
  cw.put_metric_data(Namespace=metrics.get_namespace(),
                     MetricData=metrics.get_all_metrics())
