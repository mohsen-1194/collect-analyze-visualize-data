import pandas as pd
import requests
from bs4 import BeautifulSoup
from matplotlib import pyplot as plt
from matplotlib.ticker import MaxNLocator

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
            "price": df["price"],
            "middle_price": middle_price,
            "average_price": average_price,
            "lowest_price": lowest_price,
            "highest_price": highest_price,
            "expensive_price": expensive_price,
            "most_popular_brands": most_popular_brands,
        }
    )
    return results


def visualize_data(data: dict) -> None:
    # === UNPACKING ===
    price = data["price"]
    most_popular_brands = data["most_popular_brands"].sort_values(ascending=False)
    stats = {
        "median": data["middle_price"],
        "average": data["average_price"],
        "cheapest": data["lowest_price"],
        "most expensive": data["highest_price"],
        "75% quantile": data["expensive_price"],
    }

    # === PLOTTING ===
    # --- Statistics ---
    fig1, ax1 = plt.subplots(figsize=(10, 5))
    bar_chart = ax1.bar(list(stats.keys()), list(stats.values()), color="skyblue")
    ax1.bar_label(bar_chart)
    ax1.yaxis.set_major_locator(MaxNLocator(10))
    ax1.set_title("Statistics")
    ax1.set_ylabel("Price USD")
    fig1.savefig("Price_stats.png", dpi=300, bbox_inches="tight")
    plt.close(fig1)

    # --- Price Dist ---
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    ax2.hist(price, bins=30, color="yellow", edgecolor="red")
    ax2.xaxis.set_major_locator(MaxNLocator(10))
    ax2.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax2.set_title("Price Distribution")
    ax2.set_xlabel("Price USD")
    ax2.set_ylabel("Number of Products")
    ax2.grid(axis="y", linestyle="--", alpha=0.5)
    fig2.savefig("Price_dist.png", dpi=300, bbox_inches="tight")
    plt.close(fig2)

    # --- Most Popular Brands ---
    fig3, ax3 = plt.subplots(figsize=(10, 5))
    ax3.bar(most_popular_brands.index, most_popular_brands.values, color="skyblue")
    ax3.set_title("Most Popular Brands")
    ax3.set_ylabel("Number of Models")
    ax3.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax3.grid(axis="y", alpha=0.5, linestyle="--")
    fig3.savefig("Popular_brands.png", dpi=300, bbox_inches="tight")
    plt.close(fig3)


def main() -> None:
    print("sending request...")
    response = requests.get(URL)
    if response.ok:
        print("scraping...")
        data = scrape_data(response)
        print("analyzing data...")
        cleaned_data = analyze_data(data)
        print("visualizing data...")
        visualize_data(cleaned_data)
        print("done.")
    else:
        response.raise_for_status()


if __name__ == "__main__":
    main()
