import requests
import time
from ascii_magic import AsciiArt

base_url = "https://wallhaven.cc/api/v1/w/"
id = "yqqrp7"
# id = "vpp2g5"
# id = "poo99j"
response = requests.get(base_url + id)
url = response.json()["data"]["thumbs"]["small"]
ratio = float(response.json()["data"]["ratio"])
print(ratio)
x_d = int(30 * float(ratio))
y_d = 30

file_name = "yqqrp7.jpg"
# file_name = "vpp2g5.jpg"
# file_name = "poo99j.jpg"
with open(file_name, "wb") as i:
    i.write(requests.get(url).content)

my_art = AsciiArt.from_image(file_name)
ascii_image = my_art._img_to_art(columns=50, width_ratio=ratio)
rows = ascii_image.splitlines()
for row in rows:
    print(row)
    time.sleep(0.05)
