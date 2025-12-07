import requests

# Solution One: run through os command with ascii-image-converter
import os

# Solution Two: with python library
from ascii_magic import AsciiArt

base_url = "https://wallhaven.cc/api/v1/w/"
id = "yqqrp7"
# id = "poo99j"
response = requests.get(base_url + id)
url = response.json()["data"]["thumbs"]["small"]
ratio = float(response.json()["data"]["ratio"])
print(ratio)
x_d = int(30 * float(ratio))
y_d = 30

file_name = "vpp2g5.jpg"
# file_name = "poo99j.jpg"
# with open(file_name, "wb") as i:
#     i.write(requests.get(url).content)

# os.system(f"ascii-image-converter {file_name} -C -b -W {x_d}")
os.system(f"ascii-image-converter {file_name} -C -b --dither -W {x_d}")
os.system(f"ascii-image-converter {file_name} -C -c -b --dither -W {x_d}")
# os.system(f"ascii-image-converter {file_name} -C -b --dither -d {x_d},{y_d}")


# my_art = AsciiArt.from_image(file_name)
# my_art.to_terminal(columns=50, width_ratio=ratio)
