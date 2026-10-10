#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 00-文档总览.html 渲染为 00-文档总览.pdf（Playwright/Chromium，A4，打印样式）。

用法：python3 build/html2pdf.py
"""
import pathlib
from playwright.sync_api import sync_playwright

SRC = "/oc/mov/00-文档总览.html"
OUT = "/oc/mov/00-文档总览.pdf"

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox", "--disable-gpu"])
    pg = b.new_page()
    pg.goto(pathlib.Path(SRC).as_uri(), wait_until="load")
    pg.wait_for_timeout(1500)
    pg.pdf(path=OUT, format="A4", print_background=True,
           margin={"top": "14mm", "bottom": "14mm", "left": "12mm", "right": "12mm"})
    b.close()
print("rendered", OUT)
