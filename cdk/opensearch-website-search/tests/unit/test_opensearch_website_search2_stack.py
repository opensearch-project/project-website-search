import aws_cdk as core
import aws_cdk.assertions as assertions

from opensearch_website_search2.opensearch_website_search2_stack import OpensearchWebsiteSearch2Stack

# example tests. To run these tests, uncomment this file along with the example
# resource in opensearch_website_search2/opensearch_website_search_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = OpensearchWebsiteSearch2Stack(app, "opensearch-website-search2")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
