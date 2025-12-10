import requests
import time
from ascii_magic import AsciiArt

base_url = "https://wallhaven.cc/api/v1/w/"
ids = ["yqqrp7", "vpp2g5", "poo99j"]
file_names = ["yqqrp7.jpg", "vpp2g5.jpg", "poo99j.jpg"]
# for id, file_name in zip(ids, file_names):
#     response = requests.get(base_url + id)
#     url = response.json()["data"]["thumbs"]["small"]
#     ratio = float(response.json()["data"]["ratio"])
#     print(ratio)
#     x_d = int(30 * float(ratio))
#     y_d = 30
#
#     with open(file_name, "wb") as i:
#         i.write(requests.get(url).content)

# my_art = AsciiArt.from_image(file_name)
# ascii_image = my_art._img_to_art(columns=20, width_ratio=ratio)

file_name_1 = "yqqrp7.jpg"
file_name_2 = "vpp2g5.jpg"
file_name_3 = "poo99j.jpg"
my_art_1 = AsciiArt.from_image(file_name_1)
my_art_2 = AsciiArt.from_image(file_name_2)
my_art_3 = AsciiArt.from_image(file_name_3)
ascii_image_1 = my_art_1._img_to_art(columns=20)
ascii_image_2 = my_art_2._img_to_art(columns=20)
ascii_image_3 = my_art_3._img_to_art(columns=20)

rows_1 = ascii_image_1.splitlines()
rows_2 = ascii_image_2.splitlines()
rows_3 = ascii_image_3.splitlines()

# for row_1, row_2 in zip(rows_1, rows_2):
#     print(row_1, "                 ", row_2)
#     time.sleep(0.05)

ascii_image_1 = my_art_1._img_to_art(columns=40, width_ratio=2)
ascii_image_2 = my_art_2._img_to_art(columns=40, width_ratio=3)

rows_1 = ascii_image_1.splitlines()
rows_2 = ascii_image_2.splitlines()

for i, row in enumerate(rows_1):
    if i < len(rows_2):
        print(i, row, "           ", rows_2[i])
    else:
        print(i, row)
    time.sleep(0.05)

# for row in rows:
#     print(row)
#     time.sleep(0.05)
