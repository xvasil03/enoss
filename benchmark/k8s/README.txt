Directory contains k8s sources used during benchmarking.

Elasticsearch pod needs to be created before swiss-enoss.

After elasticsearch pod is initalized, elastic password is restarted and CA cert retrieved to ./config directory (using guide https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html)
Next step is update of elastic password in ./config/destinations.conf
After CA cert is downloaded to ./config and new elastic password is stored to ./config/destinations.conf swift-enoss can be initalized.

