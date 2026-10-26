import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from matplotlib import pyplot as plt

URL = "https://webscraper.io/test-sites/e-commerce/allinone/computers/laptops"


def scrape_data(response: requests.Response) -> list:
    soup = BeautifulSoup(response.text, "html.parser")
    data = []
    for product in soup.find_all("div", class_="product-wrapper card-body"):
        price = product.find("span", itemprop="price").text
        title = product.find("a")["title"]
        desc = product.find("p", itemprop="description").text
        link = product.find("a")["href"]
        cur = product.find("meta")["content"]
        rating = product.select_one("p[data-rating]")["data-rating"]
        reviews = product.find("span", itemprop="reviewCount").text
        data.append(
            {
                "title": title,
                "description": desc,
                "price": price,
                "link": link,
                "currency": cur,
                "rating": rating,
                "n_reviews": reviews,
            }
        )
    return data


def analyze_data(data: list) -> dict:
    df = pd.DataFrame(data)
    results = {}

    # ----- some cleaning and type casting -----
    df["price"] = df["price"].str.replace("$", "")
    df["title"] = df["title"].str.lower()
    df["description"] = df["description"].str.lower()

    df = df.astype(
        {
            "title": "string",
            "description": "string",
            "currency": "string",
            "link": "string",
            "price": "float",
            "rating": "int",
            "n_reviews": "int",
        }
    )

    # ===== ANALYSIS =====
    # ----- price analysis -----
    middle_price = df["price"].median().round(2)
    average_price = df["price"].mean().round(2)
    highest_price = df["price"].max().round(2)
    lowest_price = df["price"].min().round(2)
    expensive_price = df["price"].quantile(0.75)

    # ----- brands -----
    df["brand"] = df["title"].str.split().str[0]
    df["brand"] = df["brand"].astype("string")

    # -- turn sub-brands brand name into parent brand --
    brand_mapping = {
        "hewlett": "hp",
        "packard": "hp",
        "pavilion": "hp",
        "probook": "hp",
        "aspire": "acer",
        "inspiron": "dell",
        "thinkpad": "lenovo",
    }

    df["brand"] = df["brand"].replace(brand_mapping)

    most_popular_brands: pd.Series = df["brand"].value_counts().head(5)

    results.update(
        {
            "df": df,
            "middle_price": middle_price,
            "average_price": average_price,
            "lowest_price": lowest_price,
            "highest_price": highest_price,
            "expensive_price": expensive_price,
            "most_popular_brands": most_popular_brands,
        }
    )
    return results


def visualize_data(input_data: dict) -> None:
    # === UNPACKING ===
    df = input_data["df"]
    most_popular_brands = input_data["most_popular_brands"]

    # === PLOTTING ===
    # --- Statistics ---
    fig1 = plt.figure(figsize=(10, 5))
    stats_names = ["median", "average", "cheapest", "most expensive", "75% quantile"]
    stats = [
        input_data["middle_price"],
        input_data["average_price"],
        input_data["lowest_price"],
        input_data["highest_price"],
        input_data["expensive_price"],
    ]
    bar_chart = plt.bar(stats_names, stats, color="skyblue")
    plt.bar_label(bar_chart)
    plt.yticks(np.arange(0, 2000, 200))
    plt.title("Statistics")
    plt.ylabel("Price USD")

    # --- Price Dist ---
    fig2 = plt.figure(figsize=(10, 5))
    data = df["price"]
    plt.hist(data, bins=30, color="yellow", edgecolor="red")
    plt.xticks(np.arange(200, 2000, 100))
    plt.yticks(np.arange(0, 20, 1))
    plt.title("Price Distribution")
    plt.xlabel("Price USD")
    plt.ylabel("Number of Products")
    plt.grid(axis="y", linestyle="--", alpha=0.5)

    # --- Most Popular Brands ---
    fig3 = plt.figure(figsize=(10, 5))
    plt.bar(most_popular_brands.index, most_popular_brands.values, color="skyblue")
    plt.title("Most popular brands")
    plt.ylabel("Number of Models")
    plt.grid(axis="y", alpha=0.5, linestyle="--")
    plt.yticks(np.arange(0, 30, 2))

    fig1.savefig("Price_stats.png", dpi=300)
    fig2.savefig("Price_dist.png", dpi=300)
    fig3.savefig("Popular_brands.png", dpi=300)


def main() -> None:
    response = requests.get(URL)
    if response.ok:
        data = scrape_data(response)
        cleaned_data = analyze_data(data)
        visualize_data(cleaned_data)
    else:
        print("Error with http request/response. Try again.")


if __name__ == "__main__":
    main()
