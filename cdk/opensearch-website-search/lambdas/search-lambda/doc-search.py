import json
import requests
import os
import re
from requests.auth import HTTPBasicAuth

username = os.getenv('SEARCH_USER')
password = os.getenv('SEARCH_PASS')
nlb_opensearch_port = os.getenv('NLB_OPENSEARCH_PORT', "80")
host = 'http://' + os.getenv('NLB_ENDPOINT') + ':' + nlb_opensearch_port
index = 'docs'

http_basic_auth = HTTPBasicAuth(username, password)


def handler(event, context):

  url_param_str = 'queryStringParameters'
  query_str = 'q'
  response = {
    "statusCode": 400,
    "headers": {
      "Access-Control-Allow-Origin": '*'
    },
    "isBase64Encoded": False,
    "body": ""}

  if url_param_str not in event:
    response["body"] = 'url string parameters missing'
    return response
  elif 'q' not in event[url_param_str] or event[url_param_str][query_str].strip() == '':
    # TODO: should we do a general search without query?
    response["body"] = 'Empty query parameter ("q"). Nothing to search for.'
    return response

  # Input sanitization, courtesy https://github.com/AMoo-Miki
  q = re.sub(r"([\\+=\-!(){}[\]^~*?:/'\"<>| ]|&{2,}|\b(AND|OR|NOT)\b)+", " ", event[url_param_str][query_str]).strip()

  search_url = host + '/' + index + '/_search'

  # 1. TODO: if the user and password for search is not present in ENV variable invoke a CW alarm
  # 2. TODO: modify this query to improve relevance and extract right fields based on
  #  document schema and fields required by frontend
  query = {
    "query": {
      "match": {
        "content": {
          "query": q
        }
      }
    },
    "_source": ["url", "version", "type", "summary"],
    "size": 200
  }

  # ES > 6.x requires an explicit Content-Type header
  headers = {"Content-Type": "application/json"}
  r = requests.get(search_url, auth=http_basic_auth, headers=headers, data=json.dumps(query))

  response['statusCode'] = r.status_code
  response['body'] = r.text
  return response
