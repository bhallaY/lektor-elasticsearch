# lektor-elasticsearch

lektor-elasticsearch makes it easy to deploy your Lektor project to an Elasticsearch cluster. 

## Before You Start
You need to set up an Elasticsearch cluster. This can be hosted anywhere, I used Bonsai to host mine because they had a free tier. Make sure you have an access key to this cluster because you will need to provide it here. 

You do **not** need to set up your indices first, lektor-elasticsearch can automatically create them based on your models.

## Installation and Usage
Install with the Lektor toolchain. Within your project, run 

`lektor plugins add lektor-elasticsearch`

After this, add a deployment target to your project file (*.lektorproject) containing the URL for your elasticsearch cluster. This should look like:
`[servers.elasticsearch]
name = ElasticSearch
enabled = yes
target = elasticsearch:/<CLUSTER-URL>
`

You will also need to add configuration details to the plugin specific configuration file. This would be in a top-level `configs` folder with a file called `elasticsearch.ini`. In this file you should add the following:
`[cluster]
url = <CLUSTER-URL>
access_key = <CLUSTER ACCESS KEY>
access_secret = <CLUSTER ACCESS SECRET>
port = <PORT FOR CLUSTER>`

You can also submit these as command line arguments when you call `lektor deploy elasticsearch`. This will cause Lektor to upload your website content to the Elasticsearch cluster you targeted. 

## Contributions
Any recommendations or feature requests would be very cool! 

## Current Limitations 
The bulk API is not used when transferring files to the Elasticsearch cluster.
All files of your website are currently uploaded to the Elasticsearch cluster. 
No tests for the project. I am not sure how I would go about testing this, as it is mainly API calls to the elasticsearch cluster.

If anyone wants these limitations dealt with or has suggestions for how to deal with them, please open an issue or pull request!