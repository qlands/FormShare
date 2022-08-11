import glob
import imghdr
import os

"""
This script fixes jpg images that for some reason were stored with ~ 
in an early version of FormShare.

path_to_submissions = /path/to/submissions/directory/*/

"""

path_to_submissions = "/home/me/submissions/*/"

deleted = 0
renamed = 0
ok = 0
for a_directory in glob.iglob(path_to_submissions):
    files = {}
    files_array = []

    for a_file in glob.iglob(a_directory + "*"):
        split_tup = os.path.splitext(a_file)
        if split_tup[1] == ".jpg" or split_tup[1] == ".jpg~":
            image_type = imghdr.what(a_file)
            if image_type is None:
                if split_tup[1] == ".jpg":
                    os.remove(a_file)
                    deleted = deleted + 1

    for a_file in glob.iglob(a_directory + "*"):
        split_tup = os.path.splitext(a_file)
        if split_tup[1] == ".jpg" or split_tup[1] == ".jpg~":
            image_type = imghdr.what(a_file)
            if image_type == "jpeg":
                if split_tup[1] == ".jpg~":
                    os.rename(a_file, a_file.replace(".jpg~", ".jpg"))
                    renamed = renamed + 1
                else:
                    ok = ok + 1
            else:
                print("Error: {}".format(a_file))
                exit(1)

print("Renamed: {}".format(renamed))
print("OK: {}".format(ok))
print("Deleted: {}".format(deleted))
