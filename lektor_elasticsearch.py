# -*- coding: utf-8 -*-
from lektor.pluginsystem import Plugin, get_ctx
import os, base64, re, logging, json
from datetime import datetime
from elasticsearch import Elasticsearch
from lektor.publisher import Publisher, PublishError
from lektor.context import get_ctx 
from lektor.project import Project
from lektor.types.formats import Markdown

class ElasticsearchPlugin(Plugin):
    name = 'elasticsearch'
    description = u'Creates/updates indexes that correspond to templates into an Elasticsearch cluster'

    def on_setup_env(self, **extra):
      # Connect to cluster over SSL using auth for best security:
      # make all configurations into global variables for access
      config = self.get_config()
      self.env.elasticsearch_credentials = {}
      self.env.elasticsearch_credentials['host'] = config.get('cluster.url')
      self.env.elasticsearch_credentials['port'] = config.get('cluster.port')
      self.env.elasticsearch_credentials['access_key'] = config.get('cluster.access_key')
      self.env.elasticsearch_credentials['access_secret'] = config.get('cluster.access_secret')
      # add the publisher
      if hasattr(self.env, 'publishers'):
        self.env.publishers['elasticsearch'] = ElasticsearchPublisher
      else:
        from lektor.publisher import publishers 
        publishers['elasticsearch'] = ElasticsearchPublisher
      
    ## add functions for templates here, mainly querying and all
    def find(text_to_search, category: str="body", index=None):
      """Enables a simple search for given text"""
      es = connect(sel.env.elasticsearch_credentials)
      query = {"query": {"match": {category: text_to_search}}}
      return es.search(index=index, body=query)


class ElasticsearchPublisher(Publisher):
  def __init__(self, env, output_path):
    super(ElasticsearchPublisher, self).__init__(env, output_path)
    self.es = None # attempt connection when publishing

  def publish(self, target_url, credentials=None, server_info=None, **extra):
    # check if target_url is provided. 
    if target_url.netloc != '':
      self.env.elasticsearch_credentials['host'] = target_url.netloc
    
    # merge CLI credentials with config file ones
    creds = parse_creds(self.env.elasticsearch_credentials, credentials)

    yield "Connecting to Elasticsearch cluster"
    self.es = connect(creds)

    yield "Verifying every data model has a corresponding index on cluster"
    for dirpath, dirname, filenames in os.walk("./models"):
      for filename in filenames:
        model_name = filename.split(".", 1)[0]
        if not self.model_index_exists(model_name):
          self.create_model_index(model_name)

    yield "Adding/updating docs to the cluster"
    self.add_docs()
    
    yield "Finished!"
    disconnect(self.es)
  
  def filter_data(self, model_data):
    """Removes all the System Fields from a document's data"""
    # may need to include "_path" and or _gid
    filtered_dict = {}
    for (key, value) in model_data.items():
      if key[0] != "_":
        filtered_dict[key] = value
    return filtered_dict

  def add_docs(self):
    """Adds all conent pages as a separate document to elasticsearch cluster"""
    pad = self.create_pad()
    to_process = set(pad.root.children.all())
    record_json = []
    # performing BFS to go through all 
    while to_process:
      model = to_process.pop()
      doc_as_dict = self.process_doc(model)
      es_index_name = model["_model"]
      record_json.append((es_index_name, doc_as_dict))
      to_process.update(model.children.all())
    # add to elasticsearch
    for index, body in record_json:
      self.es.index(index=index, id=body["_gid"], body=json.dumps(body))
  
  def process_doc(self, doc):
    """Takes in a content file and returns a Python dictionary representation of the file"""
    file_contents = doc.contents.as_text()
    file_parts = file_contents.split("---")
    file_as_dict = {}
    for file_part in file_parts:
      key_val = file_part.replace("\n", "").split(":")
      if key_val[0] and key_val[0][0] != "_":
        file_as_dict[key_val[0]] = key_val[1]
    file_as_dict["_gid"] = doc["_gid"]
    file_as_dict["_path"] = doc["_path"]
    return file_as_dict

  def model_index_exists(self, model):
    """Checks with Elasticsearch cluster if an index with the same name as the given model already 
    exists within cluster"""
    return self.es.indices.exists(model)

  def create_model_index(self, model):
    """Creates a new index with Elasticsearch with the same name as given model.
        Tries to map model's data fields with corresponding types in the index
        
        Note: There is no custom mapping/shard creation here. It may be included in a future 
        version, but this simply creates a new empty index.
        """
    self.es.indices.create(model)

  def create_pad(self):
    """Attempts to obtains a pad."""
    if get_ctx() is not None:
      pad = get_ctx().pad
    else:
      project = Project.discover()
      env = project.make_env()
      pad = env.new_pad()
    return pad

def parse_creds(config_file_creds, cli_creds):
  """Combine potential CLI and config file credentials.
   Prefer CLI passed credentials to a config file"""
  creds = config_file_creds
  # check if any/all credentials were passed through commandline
  if cli_creds:
    if 'host' in cli_creds and cli_creds['host'] != '':
      creds['host'] = cli_creds['host']
    if 'access_key' in cli_creds and cli_creds['access_key'] != '':
      creds['access_key'] = cli_creds['access_key']
    if 'access_secret' in cli_creds and cli_creds['access_secret'] != '':
      creds['access_secret'] = cli_creds['access_secret']
    if 'port' in cli_creds and cli_creds['port'] != '':
      creds['port'] = cli_creds['port']
  return creds
    
def connect(creds):
  """Set up a connection to configured Elasticsearch cluster"""
  try:
    # Connect to cluster over SSL using auth for best security:
    es_header = [{
      'host': creds['host'],
      'port': creds['port'],
      'use_ssl': True,
      'http_auth': (creds['access_key'], creds['access_secret'])
      }]
    return Elasticsearch(es_header)
  except Exception as e:
    raise ConnectionError('Credentials for Elasticsearch cluster not found. Please include with CLI arguments or config file')
    
def disconnect(es):
  """Convenience function to disconnect an open connection to configured Elasticsearch cluster"""
  es.transport.close()



