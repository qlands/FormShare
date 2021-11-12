import pandas as pd
import requests

"""
This script upload data updates using FormShare update API and a CSV file.
The CSV file MUST have the following structure:
|rowuuid|variable_name|variable_value|
FormShare checks if the assistant has cleaning rights over the form being updated.
"""

update_url = "https://formshare.org/api_update"
assistant_api_key = "12345678-1234-1234-1234-123456789012"

df = pd.read_csv("/path/to/my.csv")
for i in range(len(df)):
    rowuuid = df.iloc[i, 0]
    variable_name = df.iloc[i, 1]
    variable_value = df.iloc[i, 2]
    update_dict = {
        "apikey": assistant_api_key,
        "rowuuid": rowuuid,
        variable_name: variable_value,
    }
    response = requests.post(update_url, json=update_dict)
    print("{} for UUID: {}".format(response.status_code, rowuuid))
    if response.status_code != 200:
        print(response.text)
