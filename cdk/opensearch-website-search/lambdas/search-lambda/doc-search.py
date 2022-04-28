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
  query_key = 'q'
  doc_version_key = 'v'
  response = {
    "statusCode": 400,
    "headers": {
      "Access-Control-Allow-Origin": '*',
      "Content-Type": "application/json"
    },
    "isBase64Encoded": False,
    "body": "{}"}

  if (
    url_param_str not in event or
    'q' not in event[url_param_str] or
    event[url_param_str][query_key].strip() == ''
  ):
    response["body"] = json.dumps({
      "error": {
        "code": "MISSING_QUERY",
        "message": "No search query provided"
      }
    })
    return response

  # Input sanitization, courtesy https://github.com/AMoo-Miki
  # ToDo: Relax this to allow AND/OR/NOT/PRECEDENCE for `simple_query_string`
  q = re.sub(r"([\\+=\-!(){}[\]^~*?:/'\"<>| ]|&{2,}|\b(AND|OR|NOT)\b)+", " ", event[url_param_str][query_key]).strip()

  doc_version = re.sub(r"[^\d.]+", "", event[url_param_str][doc_version_key]).strip() if event[url_param_str].get(
    doc_version_key) else os.getenv('DOCS_LATEST')

  return doSearch(q, doc_version, response)


def doSearch(q, doc_version, response):
  search_url = host + '/' + index + '/_search'

  # 1. TODO: if the user and password for search is not present in ENV variable invoke a CW alarm
  # 2. TODO: modify this query to improve relevance and extract right fields based on
  #  document schema and fields required by frontend
  query = {
    "query": {
      "bool": {
        "must": [
          {
            "simple_query_string": {
              "query": q,
              "fields": ["title", "content"],
              "analyze_wildcard": True,
              "default_operator": "and"
            }
          }, {
            "bool": {
              "should": [
                {
                  "match": {
                    "version": doc_version
                  }
                }, {
                  "bool": {
                    "must_not": [
                      {
                        "match": {
                          "type": "DOCS"
                        }
                      }
                    ]
                  }
                }
              ]
            }
          }
        ]
      }
    },
    # Overriding `boundary_chars` as "\n" to get full paragraphs is not working. Will need to figure the best match ourselves.
    "highlight": {
      "no_match_size": 80,
      "fragment_size": 250,
      "pre_tags": "",
      "post_tags": "",
      "fields": {
        "content": {
          "number_of_fragments": 1
        }
      }
    },
    # `collection` is a string used by the website
    # `ancestors` is an array used by the docsite
    "_source": ["url", "version", "type", "title", "content", "ancestors", "collection"],
    "size": 200
  }

  # ES > 6.x requires an explicit Content-Type header
  headers = {"Content-Type": "application/json"}
  r = requests.get(search_url, auth=http_basic_auth, headers=headers, data=json.dumps(query))

  response['statusCode'] = r.status_code
  result = json.loads(r.text)

  if r.status_code == 200:
    output = limitResults(result['hits']['hits']) if 'hits' in result and 'hits' in result['hits'] else []
    if not output and not q.endswith('*'):
      # If no results were found, make last word act as a prefix
      return doSearch(q + "*", doc_version, response)

    response['body'] = json.dumps({"results": output})

  # Look for error key when status_code != 200
  elif 'error' in result and 'caused_by' in result['error'] and result['error']['caused_by']['reason']:
    response['body'] = json.dumps({
      "error": {
        "code": result['error']['caused_by']['type'].upper() if result['error']['caused_by']['type'] else "ERROR",
        "message": result['error']['caused_by']['reason']
      }
    })

  # If status_code != 200 and no error details found, send back unknown error
  else:
    response['body'] = json.dumps({"error": {"code": "UNKNOWN", "message": "Unknown error"}})

  return response


def limitResults(hits):
  return list(filter(bool, map(limitProperties, hits)))


def limitProperties(record):
  if '_source' not in record:
    return None

  source = record['_source']
  result = {
    "url": source['url'],
    "type": source['type'],
    "version": source['version'],
    "title": source['title']
  }

  ancestors = []
  if 'ancestors' in source and source['ancestors']:
    ancestors.extend(source['ancestors'])
  elif 'collection' in source and source['collection']:
    ancestors.append(source['collection'])

  result['ancestors'] = ancestors

  if (
    'highlight' in record and
    'content' in record['highlight'] and
    record['highlight']['content']
  ):
    result["content"] = record['highlight']['content'][0]

  return result