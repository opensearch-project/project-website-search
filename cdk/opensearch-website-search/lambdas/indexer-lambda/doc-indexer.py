import os
import base64
import boto3
import json
import random
import sys
import string
import time
import requests
from botocore.exceptions import ClientError
from opensearchpy import OpenSearch, helpers


BASE_ENDPOINT = os.environ['API_GATEWAY_ENDPOINT']  # https://<10-digit-id>.execute-api.<region>.amazonaws.com
PROXY_ENDPOINT = BASE_ENDPOINT + '/prod/opensearch'
INDEX_NAME_PREFIX = 'documentation_index'
INDEX_ALIAS = 'docs'
SECTION_SEPARATOR = '===================='


class SecretManager(object):

  def __init__(self, secret_name, region=None):
    self.secret_name = secret_name
    self.region = region if region else os.environ['AWS_REGION']
    self.username = None
    self.password = None

  def fetch_secret(self):
    session = boto3.session.Session()
    client = session.client(
      service_name='secretsmanager',
      region_name=self.region
    )

    # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # We rethrow the exception by default.

    secret = ""

    try:
      get_secret_value_response = client.get_secret_value(
        SecretId=self.secret_name
      )
      print("fetched secret")
    except ClientError as e:
      if e.response['Error']['Code'] == 'DecryptionFailureException':
        # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
        # Deal with the exception here, and/or rethrow at your discretion.
        raise e
      elif e.response['Error']['Code'] == 'InternalServiceErrorException':
        # An error occurred on the server side.
        # Deal with the exception here, and/or rethrow at your discretion.
        raise e
      elif e.response['Error']['Code'] == 'InvalidParameterException':
        # You provided an invalid value for a parameter.
        # Deal with the exception here, and/or rethrow at your discretion.
        raise e
      elif e.response['Error']['Code'] == 'InvalidRequestException':
        # You provided a parameter value that is not valid for the current state of the resource.
        # Deal with the exception here, and/or rethrow at your discretion.
        raise e
      elif e.response['Error']['Code'] == 'ResourceNotFoundException':
        # We can't find the resource that you asked for.
        # Deal with the exception here, and/or rethrow at your discretion.
        raise e
    else:
      # Decrypts secret using the associated KMS CMK.
      # Depending on whether the secret is a string or binary, one of these fields will be populated.
      if 'SecretString' in get_secret_value_response:
        secret = get_secret_value_response['SecretString']
      else:
        secret = base64.b64decode(get_secret_value_response['SecretBinary'])

    cred = json.loads(secret)
    self.username = next(iter(cred))
    self.password = cred[self.username]

  def get_username(self):
    return self.username

  def get_password(self):
    return self.password


def index_mappings():
  mappings = {
    "properties": {
      "url": {"type": "text"},
      "title": {"type": "text"},
      "content": {
        "type": "text",
        "analyzer": "html_analyzer",
        "search_analyzer": "standard"
      },
      "collection" : {"type": "text"},
      "version": {"type": "keyword"},
      "summary": {
        "type": "text",
        "index": False
      },
      "type": {"type": "keyword"}
    }
  }

  return mappings


def index_settings():
  settings = {
    "analysis": {
      "analyzer": {
        "html_analyzer": {
          "type": "custom",
          "char_filter": [
            "html_strip"
          ],
          "tokenizer": "standard",
          "filter": [
            "lowercase",
            "asciifolding",
            "stop",
            "edge_ngram"
          ]
        }
      },
      "filter": {
        "edge_ngram": {
          "type": "edge_ngram",
          "min_gram": 3,
          "max_gram": 20
        }
      }
    }
  }
  return settings


def generate_random_n_digit_string(k=8):
  # k should be integer
  # k should be greater than 0
  s = ''.join(random.choices(string.ascii_lowercase + string.digits, k=k))
  return s


def create_index_name_from_prefix(prefix=INDEX_NAME_PREFIX):
  return '{}_{}'.format(prefix, generate_random_n_digit_string())


def yield_docs(bucket, base_path, current_version, index_name):
  s3 = boto3.client('s3')  # picks up the same region where this Lambda is deployed
  index_file_key = base_path + '/search-index.json'
  obj = s3.get_object(Bucket=bucket, Key=index_file_key)
  docs_json = json.loads(obj['Body'].read().decode('utf-8'))
  # let the json.JSONDecodeError go through to calling function

  for doc in docs_json:
    doc['version'] = current_version
    yield {
      "_index": index_name,
      "_source": doc
    }


def send_success_to_pipeline(pipeline, job_id):
  job_response = pipeline.put_job_success_result(
    jobId=job_id
  )
  return job_response


def send_failure_to_pipeline(pipeline, job_id, message, invoke_id):
  job_response = pipeline.put_job_failure_result(
    jobId=job_id,
    failureDetails={
      'type': 'JobFailed',
      'message': message,
      'externalExecutionId': invoke_id
    }
  )
  return job_response


def do_indexing(os_client, job_id, user_params):

  base_path = user_params['DESTINATION_KEY']
  current_version = user_params['CURRENT_VERSION']
  bucket = user_params['BUCKET_NAME']

  print("Creating a new index")
  new_index = create_index_name_from_prefix()
  status = os_client.indices.create(index=new_index,
                                    body={
                                      "settings": index_settings(),
                                      "mappings": index_mappings()
                                    })
  print("Created a new index: ", new_index)
  print(SECTION_SEPARATOR)

  print("Listing all indices : ")
  print(os_client.cat.indices())
  print(SECTION_SEPARATOR)

  time.sleep(1)

  docs_indices = os_client.cat.aliases(name=[INDEX_ALIAS], h=['index']).split('\n')[:-1]
  docs_indices_size = len(docs_indices)
  print("docs_indices: ", docs_indices)

  if docs_indices_size > 1:
    print("Inside case docs_indices_size > 1")
    success = False
    job_message = 'Found more than one index {} for the alias {}'.format(docs_indices, INDEX_ALIAS)
    print(job_message)
  elif docs_indices_size == 0:  # initial state
    print("Inside case docs_indices_size == 0")
    # implies there was no alias or index we need to ingest all the docs
    bulk_response = helpers.bulk(os_client, yield_docs(bucket, base_path, current_version, new_index), chunk_size=5,
                                 request_timeout=20)
    print("No alias/index - BULK response: ", bulk_response)
    alias_status = os_client.indices.put_alias(new_index, INDEX_ALIAS)
    print("Alias creation status: ", bulk_response)
    print(SECTION_SEPARATOR)
  else:
    print("Inside case alias/index exists")
    old_index = docs_indices[0]
    reindex_status = helpers.reindex(os_client, old_index, new_index)
    print("Reindex Response: ", reindex_status)

    # explicitly refreshing to make sure delete_query actually deletes the document
    refresh_status = os_client.indices.refresh(new_index)
    print("Refresh Response: ", refresh_status)

    delete_query = {
      'query': {
        'term': {
          'version': {
            'value': current_version
          }
        }
      }
    }

    delete_docs_status = os_client.delete_by_query(new_index, body=delete_query)
    print("Document deletion response: ", delete_docs_status)
    # delete_status['deleted'] > 0 should be true, else attempt deleting again ?

    bulk_response = helpers.bulk(os_client, yield_docs(bucket, base_path, current_version, new_index), chunk_size=5,
                                 request_timeout=20)
    print("Existing alias - Bulk response: ", bulk_response)
    print(SECTION_SEPARATOR)

    alias_status = os_client.indices.update_aliases(
      {
        "actions": [
          {"remove": {"index": old_index, "alias": INDEX_ALIAS}},
          {"add": {"index": new_index, "alias": INDEX_ALIAS}}
        ]
      }
    )
    print("Alias update status: ", bulk_response)

    print("Listing aliases : ")
    print(os_client.cat.aliases())
    print(SECTION_SEPARATOR)

    # delete all indices with the prefix, except for the newest one
    indices_to_delete = "{}*,-{}".format(INDEX_NAME_PREFIX, new_index)
    print("Indices to delete :", indices_to_delete)
    delete_index_status = os_client.indices.delete(indices_to_delete)


def handler(event, context):

  job_id = event['CodePipeline.job']['id']
  user_params = json.loads(event['CodePipeline.job']['data']['actionConfiguration']['configuration']['UserParameters'])
  invoke_id = "abcde12345"  # context.invokeid

  pipeline = boto3.client('codepipeline')

  try:
    secret_manager = SecretManager("prod/website-search/indexer-credentials")
    secret_manager.fetch_secret()

    os_client = OpenSearch([PROXY_ENDPOINT], http_auth=(secret_manager.get_username(), secret_manager.get_password()))

    do_indexing(os_client, job_id, user_params)
  except Exception as e:
    print(str(e))
    return send_failure_to_pipeline(pipeline, job_id, str(e), invoke_id)
  else:
    return send_success_to_pipeline(pipeline, job_id)


if __name__ == '__main__':
  # placeholder if you are running on dev machine for testing
  event = None
  context = None
  sys.exit(handler(event, context))
