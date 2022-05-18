cd enoss

curl https://bootstrap.pypa.io/pip/2.7/get-pip.py --output get-pip.py
python2 get-pip.py
pip2 install -r requirements-py2.txt

pip3 install -U setuptools
pip3 install wheel
python3 setup.py sdist bdist_wheel

pip2 install dist/*whl

pip3 install greenstalk

proxy_conf=/etc/oio/sds/OPENIO/oioswift-0/proxy-server.conf
sed -i 's/^pipeline.*/pipeline = catch_errors gatekeeper healthcheck proxy-logging cache bulk tempurl proxy-logging swift3 enoss tempauth proxy-logging copy slo dlo versioned_writes proxy-logging proxy-server/g' $proxy_conf

echo "[filter:enoss]
paste.filter_factory = enoss.enoss:enoss_factory
use_destinations=beanstalkd
admin_s3_conf_path = /etc/swift/enoss/admin_s3_conf.json
destinations_conf_path = /etc/swift/enoss/destinations.conf-sample
s3_schema = /etc/swift/enoss/configuration-schema.json
" >> $proxy_conf