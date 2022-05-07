ENOSS - Event Notifications in Openstack Swift
==============================================

A middleware that enables publishing notifications containing information about occurred events in OpenStack Swift. 
Located in pipeline of proxy-server.

Key featrues
------------
The middleware heavily utilizes containers/buckets and accounts metadata. Information specifying which event should be published and where is stored in metadata of upper level. For publishing events regarding objects, the configuration is stored in container metadata, and for container events, the configuration is stored at an account level.


**Multi user environment** - since many different users communicate with OpenStack Swift, each of them can be interested in different event notifications. ENOSS solves this problem by allowing each container and account to have its notification configuration.

**Event filtering** - one of the main requirements for event notifications is allowing users to specify for which events should notifications be published - i.e., event filtering. ENOSS allows users to specify which types of events should be published (object/container creation, deletion, access, ...). ENOSS goes a little further and allows users to specify rules that must be satisfied for event notification to be published. Some rule operators are object/container name prefix/suffix and object size. For example, using this feature, users can select only events regarding objects bigger than 50Mb (operator: object size) or events regarding pictures (operator: object suffix).

**Multiple destinations** - since event notifications have multiple applications, from monitoring to automatization, it is essential that the proposed solution can publish a notification to multiple different destinations. ENOSS is fully capable of publishing event notifications to many different destinations (e.g., Beanstalkd queue, Kafka). In ENOSS, publishing notifications about a single event is not limited to only one destination. If a user wishes, it can be published to multiple destinations per single event. This feature allows event notification to be used for multiple applications simultaneously.

**Event notification structure** - depending on the application of event notification structure of notification may differ. Therefore, ENOSS supports several different notification structures, and using event notification configuration, ENOSS allows users can select a type of event notification structure.

**AWS S3 compatibility** - ENOSS puts a big emphasis on support and compatibility with AWS S3. The structure of event configuration and event names in ENOSS is compatible with AWS S3. ENOSS also supports all filtering rules from AWS S3, and the default event notification structure is compatible with AWS S3. This is all done to ease transfer users from AWS S3 to OpenStack Swift. Using the existing, well-documented protocol,  users will have an easier time learning and using event notifications in OpenStack Swift.

Configuration
-------------
**Setting event notification configuration** - in order to enable event notifications on specific container, first step is to store its configuration. For this purpose ENOSS uses API ``POST /v1/<acc>/<cont>?notification``. Authorized user sends event notification configuration using request body, ENOSS perform validation, if configuration is valid, ENOSS will store configuration to container system metadata, otherwise it will return unsuccessful HTTP code.

**Reading stored event notification configuration** - ENOSS offers reading stored notification configuration. For this purpose offers API: ``GET /v1/<acc>/<cont>?notification``.

**Configuration structure** - configuration structure is compatible with AWS S3 Event notifications configuration. 

Description of notification configuration::

    {
    "<Target>Configrations": [
      {
        "Id": "configration id",
        "TargetParams": "set of key-value pairs, used specify dynamic parameters of targeted destination (e.g., name of beanstalkd tube or name of the index in Elasticsearch)",
        "Events": "array of event types that will be published",
        "PayloadStructure": "type of event notification structure: S3 or CloudEvents (default value S3)",
        "Filter": {
          "<FilterKey>": {
            "FilterRules": [
              {
                "Name": "filter operations (i.e. prefix, sufix, size)",
                "Value": "filter value"
              }
            ]
          }
        }
      }
    ]
    }

Example of notification configuration for publishing notifications to beanstalkd queue::

  {
   "BeanstalkdConfigrations":[
      {
         "Id":"test",
         "Events":[
            "*"
         ],
         "PayloadStructure":"s3",
         "Filter":{
            "Key":{
               "FilterRules":[
                  {
                     "Name":"suffix",
                     "Value":".jpg"
                  }
               ]
            }
         }
      }
   ]
  }

**Notification payload structure** - default notification payload structure is AWS S3.
Example of published notification::

  {
   "Records":[
      {
         "eventVersion":"2.2",
         "eventSource":"swift:s3",
         "eventTime":"2022-04-12T14:04:48.189110",
         "eventName":"s3:ObjectCreated:Put",
         "userIdentity":{
            "principalId":"test,test:tester,AUTH_test"
         },
         "requestParameters":{
            "sourceIPAddress":"::ffff:127.0.0.1"
         },
         "responseElements":{
            "x-amz-request-id":"tx9a657c6753dd475699128-0062558700"
         },
         "s3":{
            "s3SchemaVersion":"1.0",
            "configurationId":"todo",
            "bucket":{
               "name":"current2",
               "ownerIdentity":{
                  "principalId":"AUTH_test"
               },
               "arn":"arn:aws:s3:::current2"
            },
            "object":{
               "key":"curr_my_object",
               "size":"0",
               "eTag":"a87ff679a2f3e71d9181a67b7542122c",
               "versionId":"1649772288.14729",
               "sequencer":"1649772288.14729"
            }
         }
      }
   ]
  }
