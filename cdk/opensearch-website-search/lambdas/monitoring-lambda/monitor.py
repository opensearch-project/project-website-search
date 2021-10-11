import json
import boto3
import requests
import os
from requests.auth import HTTPBasicAuth

username = os.getenv('MONITORING_USER')
password = os.getenv('MONITORING_PASS')
nlb_endpoint = os.getenv('NLB_ENDPOINT')
nlb_opensearch_port = os.getenv('NLB_OPENSEARCH_PORT', "80")
nlb_dashboards_port = os.getenv('NLB_OPENSEARCH_PORT', "5601")
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
  COLORS = ["green", "red", "yellow"]
  SHARD_COUNT_METRICS = ["active_primary_shards", "active_shards",
                         "delayed_unassigned_shards", "initializing_shards",
                         "relocating_shards", "unassigned_shards"]
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
    print("Successfully collected master metrics")

    # cluster health status metric
    if "status" in health:
      for color in COLORS:
        if health['status'] == color:
          metric_data.add({
            'MetricName': STATUS_PREFIX + color,
            'Value': 1.0,
            'Unit': 'Count',
            'StorageResolution': 60
          })
        else:
          metric_data.add({
            'MetricName': STATUS_PREFIX + color,
            'Value': 0.0,
            'Unit': 'Count',
            'StorageResolution': 60
          })
    print("Successfully emitted cluster status metrics")

    # Add node count metric
    if "number_of_nodes" in health:
      metric_data.add({
        'MetricName': 'Nodes',
        'Value': health["number_of_nodes"],
        'Unit': 'Count',
        'StorageResolution': 60
      })
    print("Successfully collected node count metric")

    # Add shard count metric
    for shard_type in SHARD_COUNT_METRICS:
      if shard_type in health:
        metric_data.add({
          'MetricName': SHARD_PREFIX + to_upper_camel_case(shard_type.removeprefix("_shards")),
          'Value': health[shard_type],
          'Unit': 'Count',
          'StorageResolution': 60
        })
    print("Successfully collected shard count metrics")

    # Add pending task metric
    if "number_of_pending_tasks" in health:
      metric_data.add({
        'MetricName': 'PendingTasks',
        'Value': health["number_of_pending_tasks"],
        'Unit': 'Count',
        'StorageResolution': 60
      })
    print("Successfully collected pending_tasks metrics")

    metric_data.add({
      'MetricName': 'ClusterHealth.Failed',
      'Value': 0.0,
      'Unit': 'Count',
      'StorageResolution': 60
    })
    print("All check_cluster_health metrics collected")

  except Exception as e:
    print(e)
    metric_data.add({
      'MetricName': 'ClusterHealth.Failed',
      'Value': 1.0,
      'Unit': 'Count',
      'StorageResolution': 60
    })


def handler(event, context):
  cw = boto3.client("cloudwatch")
  metrics = CWMetricData("opensearch-website-search")
  check_cluster_health(metrics)
  cw.put_metric_data(Namespace=metrics.get_namespace(),
                     MetricData=metrics.get_all_metrics())
