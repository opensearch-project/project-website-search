#Installing Oopensearch dashboards
dashboards_url="${__DASHBOARDS_URL__}"
cd /
curl "${!dashboards_url}" -o opensearch-dashboards
tar zxf opensearch-dashboards
chown -R ec2-user:ec2-user opensearch-dashboards
cd opensearch-dashboards
echo "server.host: 0.0.0.0" >> config/opensearch_dashboards.yml
sudo -u ec2-user nohup ./bin/opensearch-dashboards > dashboard_install.log 2>&1 &