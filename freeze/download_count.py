"""
Use Github API to get download counts of the Pyzo binaries.
"""


## Download the data

import requests

api_url = "https://api.github.com"
pyzo_api_url = api_url + "/repos/pyzo/pyzo"

response = requests.get(pyzo_api_url + "/releases")
assert response.status_code == 200
d = response.json()


## Process and display


alltime_count = 0

for release in reversed(d):
    print("{} @ {}".format(release["name"], release["created_at"]))
    total_count = 0
    for asset in release["assets"]:
        count = asset["download_count"]
        total_count += count
        print("    {}: {}".format(asset["name"], count))
    print("    Total: {}\n".format(total_count))
    alltime_count += total_count

print("    Alltime download count: {}".format(alltime_count))
