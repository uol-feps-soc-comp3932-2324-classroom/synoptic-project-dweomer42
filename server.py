import json
from urllib.parse import urlparse
import requests

requestArray = []
# Register everything
for i in range(5000,5006):
    requestString = "http://localhost:" + str(i)
    requestArray.append(requestString)

for i in range(5000,5006):
    #print(requestArray)
    payload = json.dumps({'nodes':requestArray})
    myjson = {'nodes':requestArray}
    print(json.loads(payload))
    response = requests.post(f'http://localhost:{i}/nodes/register',json=myjson)
    