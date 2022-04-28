import setuptools


with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="opensearch_org_search_cdk",
    version="1.0.0",

    description="Infra set up for OpenSearch cluster that powers search functionality on opensearch.org using CDK",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="Abbas Hussain abbashus@github",

    package_dir={"": "website_search_cdk"},
    packages=setuptools.find_packages(where="website_search_cdk"),

    install_requires=[
        "aws-cdk.core",
        "aws-cdk.aws-s3",
        "aws-cdk.aws-ec2",
        "aws-cdk.aws-cloudwatch",
        "aws-cdk.aws_dynamodb",
        "aws-cdk.aws-autoscaling",
        "aws-cdk.aws_elasticloadbalancingv2",
        "aws-cdk.aws_iam",
        "aws-cdk.aws_logs",
        "aws-cdk.aws_lambda",
        "aws-cdk.aws_apigateway",
        "aws-cdk.aws_events_targets",
        "aws-cdk.aws_logs"
    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: Apache Software License",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
