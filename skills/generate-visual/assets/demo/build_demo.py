#!/usr/bin/env python3
"""Builds a generic demo of the 3D cube (made-up company "acme"), no real workspace needed.

    python3 build_demo.py [output.html]

It fills allspark-template.html with demo-data.json exactly as generate-visual
does with a real allspark.md: the JSON replaces only __ALLSPARK_JSON__ and every
"<" is escaped as \\u003c. Default output: allspark-demo.html next to this script.
"""
import json, pathlib, sys

here = pathlib.Path(__file__).resolve().parent
template = (here.parent / "allspark-template.html").read_text(encoding="utf-8")
data = json.loads((here / "demo-data.json").read_text(encoding="utf-8"))
if template.count("__ALLSPARK_JSON__") != 1:
    sys.exit("the template must contain __ALLSPARK_JSON__ exactly once")
out = template.replace("__ALLSPARK_JSON__", json.dumps(data, ensure_ascii=False).replace("<", "\\u003c"))
target = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else here / "allspark-demo.html"
target.write_text(out, encoding="utf-8")
print(f"demo written to {target}")
