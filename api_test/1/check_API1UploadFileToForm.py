import requests

url = "http://192.168.0.100:5900/api/1/upload_file_to_form?apikey=e8e695ce-d20a-49d5-881a-f2922f54a64e"
xml_file = "/home/cquiros/temp/justtest.csv"

files = {"file_to_upload": open(xml_file, "rb")}

payload = {
    "user_id": "cquiros",
    "project_code": "prj001",
    "form_id": "PRISE_PPRSDGhana_2018_V1",
    "overwrite": "",
}

response = requests.post(url, files=files, data=payload, verify=False)
print("*********************88")
print(response.status_code)
print(response.content)
print("*********************88")
