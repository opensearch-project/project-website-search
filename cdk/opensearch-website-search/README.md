## CDK for deploying website search clusters

This project deploys following stacks:
1. Network stack: Sets up networking resources like VPC, subnets, AZ, security group, etc.
2. Infrastructure stack: Sets up EC2 (installs ODFE 1.13.2 by default using userdata), cloudwatch logging, network load balancer. Check your cluster log in the log group created from your stack in the cloudwatch.
3. APIGatewayLambda stack: Sets up API Gateway with various endpoints and search lambda function that points to network load balancer create in Infra stack.
4. Monitoring stack: Create an AWS Lambda function that periodically monitors backend OpenSearch cluster and sends metrics to CloudWatch.
5. Bastion stack: Creates a group EC2 instances inside an AutoScaling groups spread across AZs which acts as SSH bastion hosts and can be accessed from restricted IP ranges as defined in stack.

### CDK Installation

[Install CDK](https://docs.aws.amazon.com/cdk/latest/guide/cli.html) using `npm install -g aws-cdk`


The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Prerequisites
1. Python 3 required to run CDK
2. AWS credentials configured locally or you can pass them during deployment in app.py file. [More information](https://docs.aws.amazon.com/cdk/latest/guide/environments.html)   
3. EC2 keypair in the deploying region to passed as context variable. Make sure to store the private key safely or to AWS Secrets Manager.
4. Users and passwords for search and monitoring Lambda functions. These should be created in AWS Secrets Manager. Should be passed as environment variables or context variables on command lines. Avoid persisting them `cdk.context.json` .
```
SEARCH_USER
SEARCH_PASS
MONITORING_USER
MONITORING_PASS
```
 While OpenSearch is bootstrapped on EC2 nodes, this usernames and passwords will be fetched from AWS Secrets Manager and respective users will created along with roles and role mappings.
 

## Cluster deploy
The cdk currently only supports TAR distribution hence passing any other argument as distribution would result in error.
You can check the cdk.context.json file for the default context variables. Consider them as parameters. Enter the appropriate values for keypair, url and dashboards_url. 
Any of the context variable can be overwritten using the `-c` or `--context` flag in the deploy command.

In order to deploy the stacks follow the following steps:
1. Activate the python virtual environment
2. Enter the required values in `cdk.context.json` file:
   - cidr: CIDR to create VPC with (defaults to 10.9.0.0/21).
   - distribution: currently we only support `tar` distribution.  
   - keypair: your EC2 keypair in the deploying region. Please check that the key exists and you are deploying in the same region, 
   - url: OpenSearch download url eg:https://artifacts.opensearch.org/snapshots/bundle/opensearch/1.0.0-rc1/opensearch-1.0.0-rc1-linux-x64.tar.gz , 
   - dashboards_url: OpenSearch download url eg: https://artifacts.opensearch.org/snapshots/bundle/opensearch-dashboards/1.0.0-rc1/opensearch-dashboards-1.0.0-rc1-linux-x64.tar.gz
   
Please check that the urls are valid as they won't throw an error explicitly. These links are used in the userdata of an EC2 instance.

3. If you have all values entered in cdk.context.json:
   ```
   cdk deploy --all
   ```
   If you want to enter the parameters via command line:
    ```
    cdk deploy --all -c keypair=your_ec2_keyPair -c url=<opensearch_download_link> -c dashboards_url=<dashboards_download_link>
    ``` 
    For non-interactive shell: 
    ```
    cdk deploy --all --require-approval=never
    ```

### SSH
Both data nodes and master nodes are SSH via bastion hosts. Use [ssh-bastion-ec2](tools/ssh-bastion-ec2/ssh-bastion-ec2) tool.


## Teardown
To delete a particular stack use the command:
```
cdk destroy <stackName>
```

To delete all the created stacks together use the command
```
cdk destroy --all
```
_Note: If you deployed the stack using command line parameters (i.e. cdk.context.json has empty values), you need to pass the parameters during `cdk destroy` as well_ 
```
cdk destroy --all -c keypair=your_ec2_keyPair -c url=<opensearch_download_link> -c dashboards_url=<dashboards_download_link>
```
## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation
 
 
