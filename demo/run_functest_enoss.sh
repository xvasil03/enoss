# missing packages for running functional tests
apt-get install -y python-dev libxml2-dev libxslt-dev

# can't run single func test but whole dir
# => create dir containing only enoss test and then run tests
cd /usr/local/src/swift
mkdir test/functional_enoss
cp test/functional/__init__.py test/functional_enoss
cp test/functional/mock_swift_key_manager.py test/functional_enoss
cp test/functional/swift_test_client.py test/functional_enoss
cp test/functional/test_enoss.py  test/functional_enoss

# swap names
mv test/functional test/orig_functional
mv test/functional_enoss test/functional

# run functional test
cd /usr/local/src/swift
tox -e func

# delete and restore original functional tests
rm -r test/functional
mv test/orig_functional test/functional
