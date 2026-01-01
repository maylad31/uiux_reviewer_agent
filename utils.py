from playwright.sync_api import sync_playwright
import textstat
from bs4 import BeautifulSoup
from collections import Counter
import base64
import json
import shared_state 


def capture_page(url):
    screenshots_b64 = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.add_style_tag(
            content="* { animation: none !important; transition: none !important; }"
        )

        page.goto(url, wait_until="domcontentloaded", timeout=30000)

        viewports = {
            "desktop": (1920, 1080),
            "mobile": (375, 812)
        }

        for name, (w, h) in viewports.items():
            page.set_viewport_size({"width": w, "height": h})

            img_bytes = page.screenshot(
                full_page=True,
                type="png"
            )

            screenshots_b64.append(base64.b64encode(img_bytes).decode("utf-8"))

        html = page.content()

        perf = page.evaluate("""
            () => ({
                resources: performance.getEntriesByType('resource').length,
                domContentLoaded:
                  performance.timing.domContentLoadedEventEnd -
                  performance.timing.navigationStart
            })
        """)

        browser.close()
    
    perf = {
        "resources": perf["resources"],
        "domContentLoaded_time": perf["domContentLoaded"]
    }

    return (screenshots_b64, html, perf)





def html_analyzer(url):
    html = shared_state.URL_DATA[url][1]
    soup = BeautifulSoup(html, "html.parser")
    tags = [tag.name for tag in soup.find_all(True)]
    tag_counts = Counter(tags)

    def exists(tag):
        return tag_counts.get(tag, 0) > 0

    # Headings
    headings = {
        "h1_count": tag_counts.get("h1", 0),
        "h2_count": tag_counts.get("h2", 0),
        "h3_count": tag_counts.get("h3", 0)
    }

    max_depth = max(
        len(list(tag.parents))
        for tag in soup.find_all(True)
    )

    total_tags = len(tags)
    div_ratio = round(tag_counts.get("div", 0) / total_tags, 2) if total_tags else 0

    return json.dumps({
        "sections": {
            "header": exists("header"),
            "nav": exists("nav"),
            "main": exists("main"),
            "footer": exists("footer")
        },
        "headings": headings,
        "ctas": {
            "buttons": tag_counts.get("button", 0),
            "links": tag_counts.get("a", 0),
            "primary_cta_present": tag_counts.get("button", 0) > 0
        },
        "forms": {
            "form_count": tag_counts.get("form", 0),
            "input_count": tag_counts.get("input", 0)
        },
        "media": {
            "images": tag_counts.get("img", 0),
            "videos": tag_counts.get("video", 0)
        },
        "complexity": {
            "max_dom_depth": max_depth,
            "div_ratio": div_ratio
        }
    })

    
def get_readability_score(url):
    html = shared_state.URL_DATA[url][1]
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n",strip=True)[:500]
    return "Flesch-Kincaid Grade: "+str(textstat.flesch_kincaid_grade(text))+"\n(This is a grade formula in that a score of 9.3 means that a ninth grader would be able to read the document.)"


def image_weight_analyzer(url):
    html = shared_state.URL_DATA[url][1]
    soup = BeautifulSoup(html, "html.parser")
    images = soup.find_all("img")

    sizes = []
    for img in images:
        w = img.get("width")
        h = img.get("height")
        if w and h and w.isdigit() and h.isdigit():
            sizes.append(int(w) * int(h))

    return json.dumps({
        "image_count": len(images),
        "largest_image_pixels(w * h)": max(sizes) if sizes else 0
    })
    
