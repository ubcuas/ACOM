# utility.py

## returns request.json['key'] if the key exists
## else return given defaultValue
def parseRequest(request, key, defaultValue):
    if key in request.json:
        return request.json[key]
    else:
        return defaultValue