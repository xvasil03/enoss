def get_s3_event_name(account, container, object, method):
    res = "s3"
    if object:
        res += ":Object"
    elif container:
        res += ":Bucket"
    else:
        res += ":Account"

    if method in ["PUT", "POST", "COPY"]:
        res += "Created"
    elif method in ["DELETE"]:
        res += "Deleted"
    else:
        res += "Accessed"

    res += ":" + method.title()

    return res
