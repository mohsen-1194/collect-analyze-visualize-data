"""Tests for the scraper / analysis / visualization project.

Run with:  pytest -q

"""

import types
from unittest.mock import MagicMock

import matplotlib

matplotlib.use("Agg")  # headless backend – must be set BEFORE pyplot is imported

import matplotlib.pyplot as plt
import pandas as pd
import pytest

import scraper as app  # <-- change to your actual module name

# --------------------------------------------------------------------------- #
# Helpers & fixtures
# --------------------------------------------------------------------------- #


def make_product(
    title="Test Laptop",
    description="some description",
    price="$100",
    link="/p/x",
    currency="USD",
    rating="3",
    n_reviews="5",
):
    """Build one raw product dict as produced by scrape_data()."""
    return {
        "title": title,
        "description": description,
        "price": price,
        "link": link,
        "currency": currency,
        "rating": rating,
        "n_reviews": n_reviews,
    }


# Mimics the structure of webscraper.io's product cards (two products).
HTML_PAGE = """
<html><body>
  <div class="product-wrapper card-body">
    <a href="/product/1" title="HP Pavilion 15">HP Pavilion 15</a>
    <p itemprop="description">A great laptop</p>
    <p data-rating="4">4</p>
    <span itemprop="price">$999.99</span>
    <meta content="USD">
    <span itemprop="reviewCount">12</span>
  </div>
  <div class="product-wrapper card-body">
    <a href="/product/2" title="Acer Aspire 5">Acer Aspire 5</a>
    <p itemprop="description">Budget friendly</p>
    <p data-rating="3">3</p>
    <span itemprop="price">$499.00</span>
    <meta content="EUR">
    <span itemprop="reviewCount">7</span>
  </div>
</body></html>
"""

EXPECTED_PRODUCTS = [
    {
        "title": "HP Pavilion 15",
        "description": "A great laptop",
        "price": "$999.99",
        "link": "/product/1",
        "currency": "USD",
        "rating": "4",
        "n_reviews": "12",
    },
    {
        "title": "Acer Aspire 5",
        "description": "Budget friendly",
        "price": "$499.00",
        "link": "/product/2",
        "currency": "EUR",
        "rating": "3",
        "n_reviews": "7",
    },
]


@pytest.fixture
def fake_response():
    """Stand-in for requests.Response – scrape_data only needs .text."""
    return types.SimpleNamespace(text=HTML_PAGE, ok=True)


@pytest.fixture
def raw_products():
    """Nine products: 6 distinct brands, prices 100–900.

    Brands after normalization:
        hp    -> 3  (HP Pavilion / Hewlett Packard / ProBook)
        acer  -> 2  (Acer / Aspire)
        asus, dell, lenovo, apple -> 1 each
    """
    return [
        make_product("HP Pavilion 15", price="$100"),
        make_product("Hewlett Packard ProBook", price="$200"),
        make_product("ProBook 450", price="$300"),
        make_product("Acer Aspire 5", price="$400"),
        make_product("Aspire 3", price="$500"),
        make_product("Dell Inspiron 15", price="$600"),
        make_product("Lenovo ThinkPad X1", price="$700"),
        make_product("Apple MacBook Air", price="$800"),
        make_product("Asus VivoBook", price="$900"),
    ]


@pytest.fixture
def analyzed_payload():
    """Minimal, valid input for visualize_data()."""
    return {
        "price": pd.Series([100.0, 200.0, 300.0, 400.0]),
        "middle_price": 250.0,
        "average_price": 250.0,
        "lowest_price": 100.0,
        "highest_price": 400.0,
        "expensive_price": 325.0,
        "most_popular_brands": pd.Series({"hp": 3, "acer": 2}),
    }


# --------------------------------------------------------------------------- #
# scrape_data
# --------------------------------------------------------------------------- #


class TestScrapeData:
    def test_parses_all_fields_for_every_product(self, fake_response):
        rows = app.scrape_data(fake_response)
        assert rows == EXPECTED_PRODUCTS

    def test_returns_list_of_dicts(self, fake_response):
        rows = app.scrape_data(fake_response)
        assert isinstance(rows, list)
        assert len(rows) == 2
        assert all(isinstance(row, dict) for row in rows)

    def test_raw_values_are_strings(self, fake_response):
        # Casting happens later, in analyze_data
        row = app.scrape_data(fake_response)[0]
        for key in ("price", "rating", "n_reviews", "currency"):
            assert isinstance(row[key], str)

    def test_empty_page_returns_empty_list(self):
        response = types.SimpleNamespace(text="<html><body></body></html>")
        assert app.scrape_data(response) == []


# --------------------------------------------------------------------------- #
# analyze_data
# --------------------------------------------------------------------------- #


class TestAnalyzeData:
    def test_returns_expected_keys(self, raw_products):
        results = app.analyze_data(raw_products)
        assert set(results) == {
            "price",
            "middle_price",
            "average_price",
            "lowest_price",
            "highest_price",
            "expensive_price",
            "most_popular_brands",
        }

    def test_price_series_is_float_and_in_order(self, raw_products):
        results = app.analyze_data(raw_products)
        price = results["price"]
        assert isinstance(price, pd.Series)
        assert pd.api.types.is_float_dtype(price)
        assert price.tolist() == [
            100.0,
            200.0,
            300.0,
            400.0,
            500.0,
            600.0,
            700.0,
            800.0,
            900.0,
        ]

    def test_price_statistics(self, raw_products):
        results = app.analyze_data(raw_products)
        assert results["middle_price"] == pytest.approx(500.0)
        assert results["average_price"] == pytest.approx(500.0)
        assert results["lowest_price"] == pytest.approx(100.0)
        assert results["highest_price"] == pytest.approx(900.0)
        # 75th percentile of 100..900 (n=9) = 700
        assert results["expensive_price"] == pytest.approx(700.0)

    def test_prices_are_rounded_to_two_decimals(self):
        data = [
            make_product(price="$10.01"),
            make_product(price="$10.02"),
            make_product(price="$10.04"),
        ]
        results = app.analyze_data(data)
        # mean = 10.02333... -> 10.02 ; median = 10.02
        assert results["average_price"] == pytest.approx(10.02)
        assert results["middle_price"] == pytest.approx(10.02)

    def test_dollar_sign_is_stripped(self):
        results = app.analyze_data([make_product(price="$123.45")])
        assert results["price"].iloc[0] == pytest.approx(123.45)

    def test_brand_aggregation(self, raw_products):
        brands = app.analyze_data(raw_products)["most_popular_brands"]
        assert isinstance(brands, pd.Series)
        assert len(brands) == 5  # head(5)
        assert brands.index[0] == "hp"
        assert brands.iloc[0] == 3
        assert brands.index[1] == "acer"
        assert brands.iloc[1] == 2
        # sub-brand tokens must have been mapped away
        assert "hewlett" not in brands.index
        assert "probook" not in brands.index
        assert "aspire" not in brands.index

    @pytest.mark.parametrize(
        "title, expected_brand",
        [
            ("Hewlett Packard EliteBook", "hp"),
            ("Packard Bell EasyNote", "hp"),
            ("Pavilion 15", "hp"),
            ("ProBook 450", "hp"),
            ("HP EliteBook", "hp"),
            ("Aspire 5", "acer"),
            ("Inspiron 15", "dell"),
            ("ThinkPad X1", "lenovo"),
            ("Asus VivoBook", "asus"),
            ("MacBook Air", "macbook"),  # not mapped -> first word
        ],
    )
    def test_brand_mapping(self, title, expected_brand):
        results = app.analyze_data([make_product(title=title)])
        assert list(results["most_popular_brands"].index) == [expected_brand]

    def test_brand_mapping_is_case_insensitive(self):
        # titles are lowercased before the first token is taken
        results = app.analyze_data([make_product(title="HEWLETT PACKARD 250 G6")])
        assert list(results["most_popular_brands"].index) == ["hp"]


# --------------------------------------------------------------------------- #
# visualize_data
# --------------------------------------------------------------------------- #


class TestVisualizeData:
    def test_writes_three_png_files(self, tmp_path, monkeypatch, analyzed_payload):
        monkeypatch.chdir(tmp_path)
        plt.close("all")

        app.visualize_data(analyzed_payload)

        for filename in ("Price_stats.png", "Price_dist.png", "Popular_brands.png"):
            path = tmp_path / filename
            assert path.exists(), f"{filename} was not created"
            assert path.stat().st_size > 0, f"{filename} is empty"

    def test_closes_all_figures(self, tmp_path, monkeypatch, analyzed_payload):
        monkeypatch.chdir(tmp_path)
        plt.close("all")

        app.visualize_data(analyzed_payload)

        # no figures left open -> no memory leak / no GUI windows
        assert plt.get_fignums() == []

    def test_handles_unsorted_brand_series(
        self, tmp_path, monkeypatch, analyzed_payload
    ):
        monkeypatch.chdir(tmp_path)
        analyzed_payload["most_popular_brands"] = pd.Series({"acer": 2, "hp": 3})
        plt.close("all")

        app.visualize_data(analyzed_payload)  # must not raise

        assert (tmp_path / "Popular_brands.png").exists()


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #


class TestMain:
    def test_happy_path_calls_pipeline_in_order(self, monkeypatch, fake_response):
        get = MagicMock(return_value=fake_response)
        monkeypatch.setattr(app.requests, "get", get)

        scrape = MagicMock(return_value=["raw"])
        analyze = MagicMock(return_value={"clean": True})
        visualize = MagicMock()
        monkeypatch.setattr(app, "scrape_data", scrape)
        monkeypatch.setattr(app, "analyze_data", analyze)
        monkeypatch.setattr(app, "visualize_data", visualize)

        app.main()

        get.assert_called_once_with(app.URL)
        scrape.assert_called_once_with(fake_response)
        analyze.assert_called_once_with(["raw"])
        visualize.assert_called_once_with({"clean": True})

    def test_error_response_raises_and_stops_pipeline(self, monkeypatch):
        response = MagicMock()
        response.ok = False
        response.raise_for_status.side_effect = app.requests.HTTPError("404")
        monkeypatch.setattr(app.requests, "get", MagicMock(return_value=response))

        scrape = MagicMock()
        monkeypatch.setattr(app, "scrape_data", scrape)

        with pytest.raises(app.requests.HTTPError):
            app.main()

        response.raise_for_status.assert_called_once_with()
        scrape.assert_not_called()

    def test_end_to_end_scrape_and_analyze(self, monkeypatch):
        """Real scrape_data + analyze_data, plotting stubbed out."""
        response = types.SimpleNamespace(text=HTML_PAGE, ok=True)
        monkeypatch.setattr(app.requests, "get", lambda url: response)

        visualize = MagicMock()
        monkeypatch.setattr(app, "visualize_data", visualize)

        app.main()

        visualize.assert_called_once()
        payload = visualize.call_args.args[0]
        assert len(payload["price"]) == 2
        assert payload["price"].tolist() == [999.99, 499.00]

        # analyze_data rounds stats to 2 decimals, so compare against
        # the rounded mean rather than the raw float.
        expected_mean = round((999.99 + 499.00) / 2, 2)  # 749.5
        assert payload["average_price"] == pytest.approx(expected_mean)
