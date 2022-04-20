export URL=http://127.0.0.1:8080/v1/AUTH_test
export TOKEN=$(curl -v -H 'X-Storage-User: test:tester' -H 'X-Storage-Pass: testing' http://127.0.0.1:8080/auth/v1.0 2>&1 | grep "X-Storage-Token" | grep -oP "AUTH_[a-zA-Z0-9]*")

echo "Create container"
curl -X PUT -i -H "X-Auth-Token: $TOKEN" $URL/testcontainer

echo -e "\n"
echo "-----------------------------------------------------------------------------------------------"
echo "Enable notifications on container"
echo "-----------------------------------------------------------------------------------------------"
curl -X POST -i -H "X-Auth-Token: $TOKEN" $URL/testcontainer?notification -d @./test_s3_config.json

echo -e "\n"
echo "-----------------------------------------------------------------------------------------------"
echo "Read container notifications configuration"
echo "-----------------------------------------------------------------------------------------------"
curl -X GET -i -H "X-Auth-Token: $TOKEN" $URL/testcontainer?notification

echo -e "\n"
echo "-----------------------------------------------------------------------------------------------"
echo "Invoke event that will create notification (storing new json file to storage)"
echo "-----------------------------------------------------------------------------------------------"
curl -X PUT -i -H "X-Auth-Token: $TOKEN" -H "Content-Type: application/json" -d '{"key1":"value"}'  $URL/testcontainer/testobj.json
