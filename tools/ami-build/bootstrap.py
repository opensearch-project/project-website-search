#!/usr/bin/env python3

import os
import requests
import sys
import argparse
import string
import uuid


def get_opensearch_root():
  opensearch_root = os.environ["OPENSEARCH_ROOT"]
  if not opensearch_root:
    print("OPENSEARCH_ROOT value not set")
    sys.exit(-1)
  return opensearch_root


class UserData(object):
  user_data = None

  @classmethod
  def load_user_data(cls):
    # try to use IMDSv2, if it's available
    if not cls.user_data:
      response = requests.put(
        "http://169.254.169.254/latest/api/token",
        headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"}
      )
      headers = {}
      if response.status_code == requests.codes.ok:
        headers["X-aws-ec2-metadata-token"] = response.content

      response = requests.get(
        "http://169.254.169.254/latest/dynamic/instance-identity/document",
        headers=headers
      )
      if response.status_code != requests.codes.ok:
        # TODO: exit and log to syslog
        sys.exit(1)

      data = response.content
      try:
        cls.user_data = data.decode()
      except (UnicodeDecodeError, AttributeError):
        pass

  @classmethod
  def get_value(cls, key, default=''):
    return cls.user_data.get(key, default)


class SetupManager(object):
  yml_template = string.Template(
    """
# ======================== OpenSearch Configuration =========================
#
# NOTE: OpenSearch comes with reasonable defaults for most settings.
#       Before you set out to tweak and tune the configuration, make sure you
#       understand what are you trying to accomplish and the consequences.
#
# The primary way of configuring a node is via this file. This template lists
# the most important settings you may want to configure for a production cluster.
#
# Please consult the documentation for further information on configuration options:
# https://www.opensearch.org
#
# ---------------------------------- Cluster -----------------------------------
#
# Use a descriptive name for your cluster:
#
#cluster.name: my-application
#
# ------------------------------------ Node ------------------------------------
#
# Use a descriptive name for the node:
#
#node.name: node-1
#
# Add custom attributes to the node:
#
#node.attr.rack: r1
#
# ----------------------------------- Paths ------------------------------------
#
# Path to directory where to store the data (separate multiple locations by comma):
#
#path.data: /path/to/data
#
# Path to log files:
#
#path.logs: /path/to/logs
#
# ----------------------------------- Memory -----------------------------------
#
# Lock the memory on startup:
#
#bootstrap.memory_lock: true
#
# Make sure that the heap size is set to about half the memory available
# on the system and that the owner of the process is allowed to use this
# limit.
#
# OpenSearch performs poorly when the system is swapping the memory.
#
# ---------------------------------- Network -----------------------------------
#
# Set the bind address to a specific IP (IPv4 or IPv6):
#
#network.host: 192.168.0.1
#
# Set a custom port for HTTP:
#
#http.port: 9200
#
# For more information, consult the network module documentation.
#
# --------------------------------- Discovery ----------------------------------
#
# Pass an initial list of hosts to perform discovery when this node is started:
# The default list of hosts is ["127.0.0.1", "[::1]"]
#
#discovery.seed_hosts: ["host1", "host2"]
#
# Bootstrap the cluster using an initial set of master-eligible nodes:
#
#cluster.initial_master_nodes: ["node-1", "node-2"]
#
# For more information, consult the discovery and cluster formation module documentation.
#
# ---------------------------------- Gateway -----------------------------------
#
# Block initial recovery after a full cluster restart until N nodes are started:
#
#gateway.recover_after_nodes: 3
#
# For more information, consult the gateway module documentation.
#
# ---------------------------------- Various -----------------------------------
#
# Require explicit names when deleting indices:
#
#action.destructive_requires_name: true

cluster.name: $cluster_name
cluster.initial_master_nodes: ["seed"]
discovery.seed_providers: ec2
discovery.ec2.tag.role: master
network.host: 0.0.0.0
node.name: $node_name
node.master: $master
node.data: $data

######## Start OpenSearch Security Demo Configuration ########
# WARNING: revise all the lines below before you go into production
plugins.security.ssl.transport.pemcert_filepath: esnode.pem
plugins.security.ssl.transport.pemkey_filepath: esnode-key.pem
plugins.security.ssl.transport.pemtrustedcas_filepath: root-ca.pem
plugins.security.ssl.transport.enforce_hostname_verification: false
#plugins.security.ssl.http.enabled: $http_enabled
plugins.security.ssl.http.pemcert_filepath: esnode.pem
plugins.security.ssl.http.pemkey_filepath: esnode-key.pem
plugins.security.ssl.http.pemtrustedcas_filepath: root-ca.pem
plugins.security.allow_unsafe_democertificates: true
plugins.security.allow_default_init_securityindex: true
plugins.security.authcz.admin_dn:
  - CN=kirk,OU=client,O=client,L=test, C=de

plugins.security.audit.type: internal_opensearch
plugins.security.enable_snapshot_restore_privilege: true
plugins.security.check_snapshot_restore_write_privileges: true
plugins.security.restapi.roles_enabled: ["all_access", "security_rest_api_access"]
plugins.security.system_indices.enabled: true
plugins.security.system_indices.indices: [".opendistro-alerting-config", ".opendistro-alerting-alert*", ".opendistro-anomaly-results*", ".opendistro-anomaly-detector*", ".opendistro-anomaly-checkpoints", ".opendistro-anomaly-detection-state", ".opendistro-reports-*", ".opendistro-notifications-*", ".opendistro-notebooks", ".opendistro-asynchronous-search-response*"]
node.max_local_storage_nodes: 3
######## End OpenSearch Security Demo Configuration ########

"""
  )

  def setup_es(self, root):
    self.create_opensearch_yml(root)

  def create_opensearch_yml(self, root):
    yml_path = os.path.join(root, "config", "opensearch.yml")

    node_name = UserData.get_value("node_name")
    if 'seed' in node_name:
      pass
    else:
      node_name = "{}-{}".format(node_name, str(uuid.uuid4())[:8])

    yml_str = self.yml_template.substitute(
      cluster_name=UserData.get_value("cluster_name", "opensearch"),
      node_name=node_name,
      master=UserData.get_value("master", True),
      data=UserData.get_value("data", True),
      http_enabled=UserData.get_value("http_enabled", False)
    )

    with open(yml_path, 'w') as f:
      f.write(yml_str)

  def setup_security(self):
    """
    TODO: retrieve secretes from  AWS Secrets Manager form search and monitor users
    create roles, Can this be done after cluster is created,
    see https://opensearch.org/docs/security-plugin/access-control/api/#create-user
    users, roles, rolemappings

    PUT _plugins/_security/api/internalusers/<username>
{
  "password": "kirkpass",
  "opendistro_security_roles": ["maintenance_staff", "weapons"],
  "backend_roles": ["captains", "starfleet"],
  "attributes": {
    "attribute1": "value1",
    "attribute2": "value2"
  }
}
    """
    pass


class SecurityManager(object):
  pass


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--root", default=get_opensearch_root())
  args = parser.parse_args()
  UserData.load_user_data()
  SetupManager().setup_es(args.root)


if __name__ == '__main__':
  main()