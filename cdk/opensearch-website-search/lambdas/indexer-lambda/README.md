This AWS Lambda function indexes latest documentation to make it searchable on opensearch.org.

### Prerequisites:
- The function should have the following permissions attached to the execution role. Please substitute appropriate region and AWS account ID.

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "codepipeline:PutJobFailureResult",
                "codepipeline:PutJobSuccessResult"
            ],
            "Resource": "<arn-for-codepipeline-where-indexing-lambda-function-used>"
        },
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": "s3:GetObject",
            "Resource": "<arn-for-s3-bucket>"
        },
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": "secretsmanager:GetSecretValue",
            "Resource": "<arn-for-secret-with-indexing-permissions-to-opensearch>"
        }
    ]
}
```
For monitoring and debugging, Cloudwatch Logs can be enabled by adding the following policy:

```
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:CreateLogGroup",
                "logs:PutLogEvents"
            ],
            "Resource": [
                "<arn-for-log-group>",
                "<arn-for-log-stream>"
            ]
        }
```



- Environment Variables:

`API_GATEWAY_ENDPOINT` : The endpoint to the API gateway where OpenSearch cluster is frontended.
Example `https://<10-digit-id>.execute-api.<aws-region>.amazonaws.com`


- Credentials

Credentials (username/password) for authentication to backend. Secrets should be created in AWS Secrets Manager and corresponding user with appropriate permissions should be created in the OpenSearch backend.
You can put dummy values if the security plugin is not installed/enabled on OpenSearch.

- Dependencies
See [requirements.txt](./requirements.txt)

- Packaging for Lambda Deployment

Lambda function can be packaged as a zip file and uploaded along with its dependencies.

```
pip install --target ./package -r requirements.txt
```

```
cd package
zip -r ../my-deployment-package.zip .
```

```
cd ..
zip -g my-deployment-package.zip lambda_function.py
```

Deploy using AWS CLI

```
aws lambda update-function-code \
    --function-name  <your-lambda-function-name> \
    --zip-file fileb:/my-deployment-package.zip
```

- Execution

The function is intended to run as part of pipeline and should be run after the documentation-website is built and deployed to S3.
The function expects a `search-index.json` file that contains indexing docs generated from a jekyll plugin (`_plugins/search-indexer.rb`)


### How it works

The function first retrieves credentials (username/password) from AWS Secret Manager. It then creates an OpenSearch client.
#### Case 1:

If its an initial bootstrap, they would be no existing index. A new index will be created with random index name prefixed with `documentation_index` and all docs corresponding to current version will be created. A alias `docs` will be created pointing to this index.

#### Case 2:

A index already exists with an alias. A new index will be created with random index name prefixed with `documentation_index`.
All documents from old index will be reindexed to new index. Documents corresponding to current version will be deleted and new documents generated by jekyll plugin will be indexed. Alias will be updated to point to new index. All old inde(x/ices) with prefix `documentation_index` will be deleted except for the latest one.
