import glob
import os

import requests
from requests.auth import HTTPDigestAuth

"""
This script uploads submissions in XML format into FormShare using one thread.
Use this tool to import few submissions from External sources like BriefCase of Central
Each submission must be a directory containing the XML and medias files. For example:
/home/me/submissions/submission_001/submission_001.xml
/home/me/submissions/submission_001/image1.jpg
/home/me/submissions/submission_001/image2.jpg
/home/me/submissions/submission_002/submission_002.xml
/home/me/submissions/submission_002/image1.jpg
/home/me/submissions/submission_002/image2.jpg
/home/me/submissions/submission_002/image3.jpg

path_to_submissions = /home/me/submissions/*/

"""

path_to_submissions = "/path/to/the/submissions/*/"
url_to_project = "http://localhost:5900/user/me/project/my_project"
assistant_to_use = "assistant"
assistant_password = "123"

print(url_to_project)
print(path_to_submissions)
for a_directory in glob.iglob(path_to_submissions):
    files = {}
    files_array = []
    for a_file in glob.iglob(a_directory + "*"):
        files_array.append(a_file)
        file_name = os.path.basename(a_file)
        files[file_name] = open(a_file, "rb")
    if files:
        r = requests.post(
            url_to_project + "/push",
            auth=HTTPDigestAuth(assistant_to_use, assistant_password),
            files=files,
        )
        if r.status_code != 201:
            print("{}-{}".format(r.status_code, a_directory))

        for a_file in files_array:
            file_name = os.path.basename(a_file)
            files[file_name].close()
