# -*- coding: utf-8 -*-
# Created by aj nicolas
from datetime import datetime

import requests
import json
import os
from dateutil import parser

# While true to get a actual link
from loguru import logger


def fetch_info(url=""):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_2) AppleWebKit/537.36'
                                 '(KHTML, like Gecko) Chrome/56.0.2924.28 Safari/537.36'}

        r = requests.get(url + '.js', headers=headers)
        r1 = requests.get(url + '.json', headers=headers) # Need the additional data from this extension

    except (requests.exceptions.MissingSchema, requests.exceptions.InvalidURL, requests.exceptions.ConnectionError,
            requests.exceptions.InvalidSchema, NameError) as e:
        logger.error(f"The link \"{url}\" is invalid. Please check its formatting.")
        return False
    logger.success(f"Successfully retrieved product data from lin {url}")
    data_js = json.loads(r.content)
    data_json = json.loads(r1.content)
    data_js["updated_at"] = data_json["product"]["updated_at"]
    for var in data_json["product"]["variants"]:
        i = 0
        for variant_js in data_js["variants"]:
            if var["id"] == variant_js["id"]:
                data_js["variants"][i]["updated_at"] = var["updated_at"]
            i += 1
    return data_js


def parse_product(data):
    product = {
        "title": data["title"],
        "updated_at": parser.parse(data["updated_at"]),
        "variants": [],
    }
    for item in data["variants"]:
        variant = {
            "id": item["id"],
            "name": item["name"],
            "price": "$" + str(item["price"] / 100),
            "can_purchase": bool(item["available"]),
            "updated_at": parser.parse(item["updated_at"]),  # 2021-02-01T22:18:00-05:00
            "inventory": int(item["inventory_quantity"] if "inventory_quantity" in item else 0),
            "image": item["featured_image"]["src"] if "featured_image" in item else "",
            "link": data["url"]
        }
        product["variants"].append(variant)
    return product


def post_to_discord(item, url=""):
    if "DISCORD_WEBHOOK_URL" in os.environ:
        data = {
            "username": "Shopify Stock Checker",
            "avatar_url": "https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Flogos-download.com%2Fwp-content%2Fuploads%2F2016%2F10%2FShopify_logo_icon.png&f=1&nofb=1",
            "embeds": [
                {
                    "title": item["name"] + " IN STOCK!",
                    "type": "rich",
                    "description": "The item you are watching is back in stock and available in the merchant's store! Order yours before they run out!"
                                   f"\n\n**Price**: {item['price']}\n"
                                   f"**Inventory Available:** {item['inventory']} ",
                    "url": url,
                    "color": 1879160,
                    "image": {
                        "url": item["image"]
                    }
                }
            ]
        }
        headers = {
            "Content-Type": "application/json"
        }
        r= requests.post(os.environ["DISCORD_WEBHOOK_URL"], json=data, headers=headers)
        if r.status_code not in [200,204]:
            logger.error("There was a problem posting to your discord webhook")
        else:
            logger.success(f"Successfully posted to Discord webhook! Item {item['name']}")


if __name__ == "__main__":
    with open("./links.json", "r") as links:
        data = links.read()
        obj = json.loads(data)
    for index in range(0, len(obj)):
        shopify_product = obj[index]
        page = fetch_info(shopify_product["link"])
        if page is not False:
            data = parse_product(page)
            if shopify_product["alerted_on"] is None or parser.parse(shopify_product["alerted_on"]) < data["updated_at"]:
                alerted = False
                for variant in data["variants"]:
                    if variant["can_purchase"]:
                        alerted = True
                        post_to_discord(variant, url=shopify_product["link"] + "?variant=" + str(variant["id"]))
                if alerted:
                    now = datetime.utcnow()
                    obj[index]["alerted_on"] = now.strftime("%Y-%m-%dT%H:%M:%S%z+00:00")

    with open('links.json', 'w') as f:
        json.dump(obj, f)

