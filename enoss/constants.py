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

supported_s3_events = {
    "*",
    "s3:TestEvent",
    # object
    "s3:Object*",
    "s3:ObjectCreated:*",
    "s3:ObjectCreated:Put",
    "s3:ObjectCreated:Post",
    "s3:ObjectCreated:Copy",
    "s3:ObjectRemoved:*",
    "s3:ObjectRemoved:Delete",
    "s3:ObjectAccessed:*"
    "s3:ObjectAccessed:Get",
    "s3:ObjectAccessed:Head"
    # bucket
    "s3:Bucket*",
    "s3:BucketCreated:*",
    "s3:BucketCreated:Put",
    "s3:BucketCreated:Post",
    "s3:BucketCreated:Copy",
    "s3:BucketRemoved:*",
    "s3:BucketRemoved:Delete",
    "s3:BucketAccessed:*"
    "s3:BucketAccessed:Get",
    "s3:BucketAccessed:Head"
    # account
    "s3:Account*",
    "s3:AccountCreated:*",
    "s3:AccountCreated:Put",
    "s3:AccountCreated:Post",
    "s3:AccountCreated:Copy",
    "s3:AccountRemoved:*",
    "s3:AccountRemoved:Delete",
    "s3:AccountAccessed:*"
    "s3:AccountAccessed:Head"
    "s3:AccountAccessed:Get",
}
