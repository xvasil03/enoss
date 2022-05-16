#!/bin/bash

echo "creating config map enoss-configmap"

kubectl delete configmap enoss-configmap

kubectl create configmap enoss-configmap --from-file=http_ca.crt=./config/http_ca.crt \
--from-file=proxy-server.conf=./config/proxy-server.conf \
--from-file=destinations.conf=./config/destinations.conf

echo "done"
