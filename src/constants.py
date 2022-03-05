

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
