import requests
import glob
from requests.auth import HTTPDigestAuth

headers = {"Content-Type": "text/xml"}
for xml_file in glob.iglob(
    "/home/cquiros/temp/json/60ed8655-e055-4592-bf3c-91af25fd5e2f/submissions/*.xml"
):
    xml_file = {"file": open(xml_file, "rb")}
    r = requests.post(
        "http://192.168.0.101:5900/user/cquiros/project/prj001/push",
        auth=HTTPDigestAuth("ktavenner", "123"),
        files=xml_file,
    )
    print(xml_file)
    print(r.status_code)
