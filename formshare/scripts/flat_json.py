import json
from pandas.io.json import json_normalize
from collections import OrderedDict
import pandas as pd
import glob


def flatten_json(y):
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')
        elif type(x) is list:
            i = 1
            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        else:
            out[name[:-1]] = x

    flatten(y)
    return out

dataframe_array = []
files = glob.glob('/home/cquiros/temp/formshare/tmp/3058037d-140e-46ad-994f-23ad4c147a17/*.json')
for aFile in files:
    with open(aFile) as json_file:
        data = json.load(json_file)
    flat = flatten_json(data)
    with_order = OrderedDict(flat)
    temp = json_normalize(with_order)
    dataframe_array.append(temp)

# with open('/home/cquiros/temp/formshare/tmp/40c87451-18c3-4d2c-b140-83bb06fea968/7a7ba59f-4052-4b46-8c22-89eee420c4a0.json') as json_file:
#     data = json.load(json_file)
# flat = flatten_json(data)
# with_order = OrderedDict(flat)
# temp = json_normalize(with_order)
#
# with open('/home/cquiros/temp/formshare/tmp/40c87451-18c3-4d2c-b140-83bb06fea968/3d10e3fe-f5eb-4e30-a62a-9d6e9a58c506.json') as json_file:
#     data = json.load(json_file)
# flat = flatten_json(data)
# with_order = OrderedDict(flat)
# temp2 = json_normalize(with_order)

join = pd.concat(dataframe_array, sort=False)
join.to_csv("/home/cquiros/temp/formshare/tmp/3058037d-140e-46ad-994f-23ad4c147a17/hola.csv")



