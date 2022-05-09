apt-get install -y python2.7 python3-dev tox liberasurecode-dev git gcc
cp /usr/local/src/swift/test/sample.conf /etc/swift/test.conf

# create copy of original requirements
cp /usr/local/src/swift/requirements.txt /usr/local/src/swift/orig_requirements.txt

# add enoss requirements
echo "enoss" >> /usr/local/src/swift/requirements.txt
cat /enoss/requirements.txt >> /usr/local/src/swift/requirements.txt
# remove duplicity
sort -u /usr/local/src/swift/requirements.txt -o /usr/local/src/swift/requirements.txt

# do tests
cd /usr/local/src/swift
tox -e py38 test/unit/common/middleware/test_enoss.py

# restore original requirements
cp /usr/local/src/swift/orig_requirements.txt /usr/local/src/swift/requirements.txt
rm /usr/local/src/swift/orig_requirements.txt
