OPENASTACK SWIFT DEMO WITH ENOSS ENABLED

Command (might need root privileges):

bash run_docker_demo.sh

will build and create docker container having OpenStack Swift storage with ENOSS enabled.

After init phase, unit and functional ENOSS test will be runned.

Then demo stars: enables notification configuration on container and then creates event which will invoke notification.
Notifications are published to beanstalkd queue running on same container.

Lastly, beanstalk listener will be called and will print all incoming messages from beanstalkd.
