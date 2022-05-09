# Copyright (c) 2022 Nemanja Vasiljevic <xvasil03@gmail.com>.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from setuptools import setup, find_namespace_packages

VERSION = '0.0.1-2'
DESCRIPTION = 'Event Notifications in OpenStack Swift'

with open("README.rst", "r", encoding="utf-8") as fh:
    LONG_DESCRIPTION = fh.read()

# Setting up
setup(
       # the name must match the folder name 'verysimplemodule'
        name="enoss",
        version=VERSION,
        author="Nemanja Vasiljevic",
        author_email="<xvasil03@gmail.com>",
        url="https://github.com/xvasil03/enoss",
        license="Apache Software",
        zip_safe=False,
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        long_description_content_type="text/x-rst",
        packages=find_namespace_packages(include=["enoss*"]),
        install_requires=["jsonschema"],
        keywords=['openstack swift', 'event notifications'],
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Environment :: OpenStack",
            "Intended Audience :: Information Technology",
            "Intended Audience :: System Administrators",
            "License :: OSI Approved :: Apache Software License",
            "Operating System :: POSIX :: Linux",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9"
        ],
        options={"bdist_wheel": {"universal": "1"}}
)
