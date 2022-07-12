import glob
import os
import datetime
import requests
from requests.auth import HTTPDigestAuth
from multiprocessing import Process
import numpy as np

"""
This script uploads submissions into FormShare.
It is useful when submissions are coming from External sources like Ona
Each submission must be a directory containing the JSON and medias files. For example:
/home/me/submissions/submission_001/submission_001.json
/home/me/submissions/submission_001/image1.jpg
/home/me/submissions/submission_001/image2.jpg
/home/me/submissions/submission_002/submission_002.json
/home/me/submissions/submission_002/image1.jpg
/home/me/submissions/submission_002/image2.jpg
/home/me/submissions/submission_002/image3.jpg

path_to_submissions = /home/me/submissions/*/

"""

path_to_submissions = "/path/to/the/submissions/*/"
url_to_project = "http://localhost:5900/user/me/project/my_project"
assistant_to_use = "assistant"
assistant_password = "123"


def process_directories(directories):
    for a_directory in directories:
        files = {}
        files_array = []
        for a_file in glob.iglob(a_directory + "*"):
            files_array.append(a_file)
            file_name = os.path.basename(a_file)
            files[file_name] = open(a_file, "rb")
        if files:
            r = requests.post(
                url_to_project + "/push_json",
                auth=HTTPDigestAuth(assistant_to_use, assistant_password),
                files=files,
            )
            print(r.status_code)
            for a_file in files_array:
                file_name = os.path.basename(a_file)
                files[file_name].close()


print(path_to_submissions)
start_time = datetime.datetime.now()

number_of_threads = 6
directory_list = glob.glob(path_to_submissions)
arrays = np.array_split(np.array(directory_list), number_of_threads)

threads = list()
for ii in range(len(arrays)):
    keywords = {"directories": arrays[ii]}
    process = Process(target=process_directories, kwargs=keywords)
    process.start()
    threads.append(process)
for process in threads:
    process.join()


end_time = datetime.datetime.now()
time_delta = end_time - start_time
total_seconds = time_delta.total_seconds()
minutes = total_seconds / 60
print("Finished in {} minutes".format(minutes))
