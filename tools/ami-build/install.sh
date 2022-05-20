#!/usr/bin/env bash


# sleep to prevent yum lock problems
# Existing lock /var/run/yum.pid: another copy is running as pid <some-pid>.
sleep 5
sudo yum update -y
sudo yum install -y libnss3.so xorg-x11-fonts-100dpi xorg-x11-fonts-75dpi xorg-x11-utils xorg-x11-fonts-cyrillic xorg-x11-fonts-Type1 xorg-x11-fonts-misc fontconfig freetype

#Installing OpenSearch from tar distribution
echo "========INSTALLING AND SETTING UP OPENSEARCH ================"
OPENSEARCH_TAR_URL="https://artifacts.opensearch.org/releases/bundle/opensearch/1.1.0/opensearch-1.1.0-linux-x64.tar.gz"
cd ~ || exit
curl "$OPENSEARCH_TAR_URL" -o opensearch
tar zxf opensearch
chown -R ec2-user:ec2-user  opensearch-*
rm -rf opensearch
mv opensearch-* opensearch
cd opensearch || exit
sudo -u ec2-user bin/opensearch-plugin install discovery-ec2 --batch
sudo -u ec2-user bin/opensearch-plugin install repository-s3 --batch
sudo -u ec2-user mkdir systemd
sudo -u ec2-user touch install.log

#Installing OpenSearch Dashboards from tar distribution
echo "========INSTALLING AND SETTING UP OPENSEARCH DAHSBOARDS ================"
dashboards_url="https://artifacts.opensearch.org/releases/bundle/opensearch-dashboards/1.1.0/opensearch-dashboards-1.1.0-linux-x64.tar.gz"
cd ~ || exit
curl "$dashboards_url" -o opensearch-dashboards
tar zxf opensearch-dashboards
chown -R ec2-user:ec2-user opensearch-dashboards-*
rm -rf opensearch-dashboards
mv opensearch-dashboards-* opensearch-dashboards
cd opensearch-dashboards || exit
sudo -u ec2-user mkdir systemd
sudo -u ec2-user touch dashboard_install.log

#Create virtualenv to run bootstrap.py
echo "========SETTING UP BOOTSTRAP ENV ================"
cd ~ || exit
sudo -u ec2-user mkdir -p scripts
sudo -u ec2-user touch scripts/requirements.txt
cd scripts || exit
{
echo "
boto3==1.18.38
botocore==1.21.38
requests==2.26.0
"
} >> requirements.txt
python3 -m venv .initenv
source .initenv/bin/activate
pip3 install -r requirements.txt
pip3 list
deactivate
ls -al

sudo groupadd -r opensearch
sudo useradd --system --no-create-home --home-dir /nonexistent --gid opensearch --shell /sbin/nologin --comment "opensearch user" opensearch
echo "Hurray! Please verify if everything has installed as expected"