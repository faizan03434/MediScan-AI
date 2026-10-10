import json
import sys
from PIL import Image, ImageDraw

matrix = json.load(open(sys.argv[1], encoding="utf-8"))
scale, quiet = 12, 4
image = Image.new("RGB", ((len(matrix) + quiet * 2) * scale,) * 2, "white")
draw = ImageDraw.Draw(image)
for y, row in enumerate(matrix):
    for x, dark in enumerate(row):
        if dark:
            x0, y0 = (x + quiet) * scale, (y + quiet) * scale
            draw.rectangle((x0, y0, x0 + scale - 1, y0 + scale - 1), fill="black")
image.save(sys.argv[2])
