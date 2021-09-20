#!/bin/bash
downloadUrl="${__URL__}"
stackName="${__STACK_NAME__}"
nodeName="${__NODE_NAME__}"
master="${__MASTER__}"
data="${__DATA__}"
ingest="${__INGEST__}"
logGroup="${__LG__}"


sudo sysctl -w vm.max_map_count=262144
sudo yum update -y
sudo yum install -y libnss3.so xorg-x11-fonts-100dpi xorg-x11-fonts-75dpi xorg-x11-utils xorg-x11-fonts-cyrillic xorg-x11-fonts-Type1 xorg-x11-fonts-misc fontconfig freetype
curl "${!downloadUrl}" -o opensearch
tar zxf opensearch
chown -R ec2-user:ec2-user opensearch*
cd opensearch-*
# TODO: Should discovery.ec2.tag.role be same as cluster.name, used for master discovery or all nodes in a cluster discovery?
{
echo "
cluster.name: ${!stackName}
cluster.initial_master_nodes: [\"seed\"]
discovery.seed_providers: ec2
discovery.ec2.tag.role: master
network.host: 0.0.0.0
node.name: ${!nodeName}
node.master: ${!master}
node.data: ${!data}
node.ingest: ${!ingest}
"
} >> config/opensearch.yml
uuid=$(uuidgen | cut -d - -f 1)
sudo sed -i /^node.name/s/node/"$uuid"/2 config/opensearch.yml
# Disabling HTTPS since all calls within VPC
sudo sed -i /plugins.security.ssl.http.enabled/s/true/false/1 plugins/opensearch-security/tools/install_demo_configuration.sh
sudo bin/opensearch-plugin install https://artifacts.opensearch.org/snapshots/native-plugins/opensearch/discovery-ec2/discovery-ec2-1.0.0-SNAPSHOT.zip --batch
sudo -u ec2-user touch install.log
sudo -u ec2-user nohup ./opensearch-tar-install.sh > install.log 2>&1 &
logfile=$(pwd)/logs/${!stackName}.log

# Creating cloudwatch logging
sudo yum install amazon-cloudwatch-agent -y
cat <<- EOF > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
{
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "$logfile",
                        "log_group_name": "${!logGroup}",
                        "log_stream_name": "${!nodeName}",
                        "timezone": "UTC"
                    }
                ]
            }
        }
    },
    "log_stream_name": "others"
}
EOF
sudo systemctl start amazon-cloudwatch-agent