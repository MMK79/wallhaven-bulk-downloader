from pandas.io.clipboard import clipboard_get

text = clipboard_get()
print(text)

import pyperclip

print(dir(pyperclip))
