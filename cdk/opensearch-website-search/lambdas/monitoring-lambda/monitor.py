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
  # TODO: whether cluster is RED, YELLOW or GREEN, this is not bullet proof code
  cluster_health_url = opensearch_base_url + '/_cluster/health?pretty'
  # ES 6.x requires an explicit Content-Type header
  headers = {"Content-Type": "application/json"}

  val = 0
  try:
    res = requests.get(cluster_health_url, auth=http_basic_auth, headers=headers, verify=False)
    health = res.json()
    if health['status'] == 'green':
      val = 1
  except Exception as e:
    print(e)

  metric_data.add({
    'MetricName': 'ClusterHealth',
    'Value': val,
    'Unit': 'Count',
    'StorageResolution': 60
  })


def handler(event, context):
  cw = boto3.client("cloudwatch")
  metrics = CWMetricData("opensearch-website-search")
  check_cluster_health(metrics)
  cw.put_metric_data(Namespace=metrics.get_namespace(),
                     MetricData=metrics.get_all_metrics())


