from aws_cdk import (aws_apigateway as gateway, aws_ec2 as ec2, aws_lambda, aws_logs, core as cdk)
import os


class ApiLambdaStack(cdk.Stack):

  def __init__(self, scope: cdk.Construct, construct_id: str, vpc, nlb, opensearch_listener, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    stack_prefix = self.node.try_get_context("stack_prefix")
    allowed_origins = self.node.try_get_context("allowed_origins")
    if allowed_origins is None or not isinstance(allowed_origins, list) or allowed_origins == '':
      raise ValueError("Please provide a list of allowed origins for CORS support")

    nlb_opensearch_port = self.node.try_get_context("nlb_opensearch_port") or "80"
    nlb_dashboards_port = self.node.try_get_context("nlb_dashboards_port") or "5601"

    search_user = self.node.try_get_context("search_user")
    search_pass = self.node.try_get_context("search_pass")

    # TODO: Configure Lambda provisioned concurrency
    search_lambda = aws_lambda.Function(self, 'search-lambda',
                                        handler='doc-search.handler',
                                        runtime=aws_lambda.Runtime.PYTHON_3_9,
                                        code=aws_lambda.Code.asset('lambdas/search-lambda'),
                                        vpc=vpc,
                                        vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE),
                                        environment={
                                          'SEARCH_USER': os.getenv("SEARCH_USER", search_user),
                                          'SEARCH_PASS': os.getenv("SEARCH_PASS", search_pass),
                                          'NLB_ENDPOINT': nlb.load_balancer_dns_name,
                                          'NLB_OPENSEARCH_PORT': self.node.try_get_context("nlb_opensearch_port") or 80,
                                        })

    """
    https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-logging.html
    
    default access log format used
    { "requestId":"$context.requestId", "ip": "$context.identity.sourceIp", 
    "caller":"$context.identity.caller", "user":"$context.identity.user",
    "requestTime":"$context.requestTime", "httpMethod":"$context.httpMethod",
    "resourcePath":"$context.resourcePath", "status":"$context.status",
    "protocol":"$context.protocol", "responseLength":"$context.responseLength" }
    """
    gateway_access_log_group = aws_logs.LogGroup(self, "LogGroup",
                                                 log_group_name=f'{stack_prefix}api-gateway/access-logs',
                                                 retention=aws_logs.RetentionDays.THREE_MONTHS)

    access_log_destination = gateway.LogGroupLogDestination(gateway_access_log_group)

    stage_options = gateway.StageOptions(
      logging_level=gateway.MethodLoggingLevel.INFO,
      metrics_enabled=True,
      throttling_burst_limit=5000,  # Default value is 5000
      throttling_rate_limit=10000,  # Default value is 10000
      stage_name='prod',  # Default is prod, need a better name, this becomes part of URI
      access_log_destination=access_log_destination
    )

    api = gateway.RestApi(self, stack_prefix + 'opensearch-api-gateway',
                          rest_api_name=stack_prefix + 'opensearch-api-gateway',
                          description="APIs for search and managing OpenSearch cluster",
                          deploy_options=stage_options
                          )

    search_entity = api.root.add_resource(
      'search',
      default_cors_preflight_options=gateway.CorsOptions(
        allow_methods=['GET', 'OPTIONS'],
        allow_origins=allowed_origins
      )
    )

    search_entity_lambda_integration = gateway.LambdaIntegration(search_lambda, proxy=True)
    search_entity.add_method('GET', search_entity_lambda_integration)

    # create a VPC link
    vpc_link = gateway.VpcLink(self, stack_prefix + 'opensearch-vpcLink', targets=[nlb],
                               vpc_link_name='OpenSearchVpcLink')

    # create HTTP Proxy integration to access opensearch
    opensearch_http_proxy_integration = gateway.Integration(
      type=gateway.IntegrationType.HTTP_PROXY,
      integration_http_method='ANY',
      options=gateway.IntegrationOptions(
        vpc_link=vpc_link,
        cache_key_parameters=["method.request.path.proxy"],
        request_parameters={
          "integration.request.path.proxy": "method.request.path.proxy"
        },
        integration_responses=[gateway.IntegrationResponse(
          status_code="200"
        )]
      ),
      uri=f'http://{nlb.load_balancer_dns_name}:{nlb_opensearch_port}/' + '{proxy}'
    )

    # create HTTP Proxy integration to access opensearch dashboards
    opensearch_dashboard_http_proxy_integration = gateway.Integration(
      type=gateway.IntegrationType.HTTP_PROXY,
      integration_http_method='ANY',
      options=gateway.IntegrationOptions(
        vpc_link=vpc_link,
        cache_key_parameters=["method.request.path.proxy"],
        request_parameters={
          "integration.request.path.proxy": "method.request.path.proxy"
        },
        integration_responses=[gateway.IntegrationResponse(
          status_code="200"
        )]
      ),
      uri=f'http://{nlb.load_balancer_dns_name}:{nlb_dashboards_port}/' + '{proxy}'
    )

    opensearch_access_entity = api.root.add_resource('opensearch').add_resource('{proxy+}')
    opensearch_access_entity.add_method(
      http_method='ANY',
      integration=opensearch_http_proxy_integration,
      operation_name='ReadWriteAccessOpenSearch',
      request_parameters={
        "method.request.path.proxy": True
      }
    )

    opensearch_dashboard_access_entity = api.root.add_resource('opensearch-dashboards').add_resource('{proxy+}')
    opensearch_dashboard_access_entity.add_method(
      http_method='ANY',
      integration=opensearch_dashboard_http_proxy_integration,
      operation_name='AccessOpenSearchDashboards',
      request_parameters={
        "method.request.path.proxy": True
      }
    )
