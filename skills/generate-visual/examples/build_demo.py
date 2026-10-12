#!/usr/bin/env python3
"""Rebuilds allspark-demo.html from demo.json and the template.

Same thing generate-visual does with a real allspark.md: copy the template and
replace the single data block (escaping "<"). Python standard library only.

    python3 build_demo.py            # writes allspark-demo.html next to this file
    python3 build_demo.py --check    # exits 1 if allspark-demo.html is out of date
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "allspark-template.html")
DATA = os.path.join(HERE, "demo.json")
OUT = os.path.join(HERE, "allspark-demo.html")
TOKEN = "__ALLSPARK_JSON__"


def build():
    with open(TEMPLATE, encoding="utf-8") as f:
        tpl = f.read()
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    if tpl.count(TOKEN) != 1:
        sys.exit("the template must contain %s exactly once" % TOKEN)
    blob = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    return tpl.replace(TOKEN, blob)


if __name__ == "__main__":
    html = build()
    if "--check" in sys.argv:
        current = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if current != html:
            sys.exit("allspark-demo.html is out of date: run build_demo.py")
        print("allspark-demo.html is up to date")
    else:
        with open(OUT, "w", encoding="utf-8", newline="\n") as f:
            f.write(html)
        print("wrote", OUT)
