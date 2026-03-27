from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.arima.model import ARIMA


PIPELINE_STAGES = [
    "Retail Data",
    "Data Cleaning",
    "Feature Engineering",
    "Customer Segmentation",
    "Demand Forecasting",
    "Anomaly Detection",
    "Retail Health Score",
    "AI Decision Recommendations",
    "Interactive Dashboard",
]

REQUIRED_COLUMNS = [
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
]

COLUMN_ALIASES = {
    "invoice": "Invoice",
    "invoiceno": "Invoice",
    "stockcode": "StockCode",
    "stock_code": "StockCode",
    "description": "Description",
    "productdescription": "Description",
    "quantity": "Quantity",
    "qty": "Quantity",
    "invoicedate": "InvoiceDate",
    "date": "InvoiceDate",
    "unitprice": "UnitPrice",
    "price": "UnitPrice",
    "customerid": "CustomerID",
    "customer_id": "CustomerID",
    "customer": "CustomerID",
    "country": "Country",
}


@dataclass
class RetailIntelligenceArtifacts:
    raw_data: pd.DataFrame
    clean_data: pd.DataFrame
    customer_features: pd.DataFrame
    segment_summary: pd.DataFrame
    daily_metrics: pd.DataFrame
    forecast: pd.DataFrame
    anomalies: pd.DataFrame
    country_summary: pd.DataFrame
    health_components: pd.DataFrame
    recommendations: List[Dict[str, str]]
    kpis: Dict[str, float]
    cleaning_summary: Dict[str, float]
    ingestion_summary: Dict[str, object]
    forecast_metrics: Dict[str, float]
    funnel_proxy: pd.DataFrame
    health_score: int
    health_status: str
    refreshed_at: pd.Timestamp


def _canonicalize_label(value: object) -> str:
    text = str(value).strip().replace("\ufeff", "").replace("\x00", "")
    return "".join(character.lower() for character in text if character.isalnum())


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    for column in df.columns:
        clean_name = str(column).strip().replace("\ufeff", "").replace("\x00", "")
        alias_key = _canonicalize_label(clean_name)
        renamed[column] = COLUMN_ALIASES.get(alias_key, clean_name)
    return df.rename(columns=renamed)


def _promote_first_row_to_header_if_needed(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    recognized_columns = sum(column in REQUIRED_COLUMNS for column in df.columns)
    if recognized_columns >= 4:
        return df

    first_row = df.iloc[0].tolist()
    normalized_first_row = [_normalize_columns(pd.DataFrame(columns=[value])).columns[0] for value in first_row]
    recognized_first_row = sum(value in REQUIRED_COLUMNS for value in normalized_first_row)

    generic_columns = all(
        str(column).startswith("Unnamed") or _canonicalize_label(column).isdigit()
        for column in df.columns
    )
    if recognized_first_row >= 4 or generic_columns:
        promoted = df.iloc[1:].copy().reset_index(drop=True)
        promoted.columns = normalized_first_row
        return promoted

    return df


def _read_source_bytes(source) -> tuple[bytes, str]:
    source_name = getattr(source, "name", str(source))
    if hasattr(source, "seek"):
        source.seek(0)
    if hasattr(source, "read"):
        payload = source.read()
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        if hasattr(source, "seek"):
            source.seek(0)
        return payload, source_name

    with open(source, "rb") as handle:
        return handle.read(), source_name


def _detect_delimiter(sample_text: str) -> str:
    try:
        detected = csv.Sniffer().sniff(sample_text, delimiters=",;\t|")
        return detected.delimiter
    except csv.Error:
        for delimiter in [",", ";", "\t", "|"]:
            if delimiter in sample_text:
                return delimiter
    return ","


def _read_csv_with_fallbacks(payload: bytes) -> tuple[pd.DataFrame, str, str]:
    if payload[:2] in {b"PK", b"\xD0\xCF"}:
        raise ValueError(
            "The uploaded file looks like an Excel workbook, not a plain CSV. Export it as CSV UTF-8 and upload again."
        )

    encodings = [
        "utf-8-sig",
        "utf-8",
        "utf-16",
        "utf-16-le",
        "utf-16-be",
        "ISO-8859-1",
        "cp1252",
    ]
    parsing_errors: List[str] = []

    for encoding in encodings:
        try:
            decoded = payload.decode(encoding)
        except UnicodeDecodeError as error:
            parsing_errors.append(f"{encoding}: {error}")
            continue

        normalized = decoded.replace("\x00", "")
        delimiter = _detect_delimiter("\n".join(normalized.splitlines()[:5]))
        read_options = [
            {"engine": "python", "sep": delimiter},
            {"engine": "python", "sep": delimiter, "on_bad_lines": "skip"},
            {"engine": "python", "sep": None},
            {"engine": "python", "sep": None, "on_bad_lines": "skip"},
        ]

        for options in read_options:
            try:
                frame = pd.read_csv(io.StringIO(normalized), **options)
                frame.columns = [str(column).replace("\x00", "").strip() for column in frame.columns]
                if len(frame.columns) > 1 and len(frame) > 0:
                    return frame, encoding, delimiter
            except Exception as error:
                parsing_errors.append(f"{encoding}/{delimiter}: {error}")

        # Last-resort salvage for malformed exports with sporadic bad bytes.
        try:
            relaxed = payload.decode(encoding, errors="replace").replace("\x00", "")
            frame = pd.read_csv(
                io.StringIO(relaxed),
                engine="python",
                sep=delimiter,
                on_bad_lines="skip",
            )
            frame.columns = [str(column).replace("\x00", "").strip() for column in frame.columns]
            if len(frame.columns) > 1 and len(frame) > 0:
                return frame, f"{encoding} (repaired)", delimiter
        except Exception as error:
            parsing_errors.append(f"{encoding}/{delimiter}/repaired: {error}")

    raise ValueError(
        "Unable to parse the uploaded CSV. "
        f"Tried multiple encodings and delimiters. Last parser details: {parsing_errors[-1] if parsing_errors else 'unknown error'}"
    )


def load_retail_data(source) -> tuple[pd.DataFrame, Dict[str, object]]:
    payload, source_name = _read_source_bytes(source)
    df, encoding_used, delimiter_used = _read_csv_with_fallbacks(payload)
    df = _normalize_columns(df)
    df = _promote_first_row_to_header_if_needed(df)
    df = _normalize_columns(df)

    html_signature = {_canonicalize_label(column) for column in df.columns[:5]}
    if {"doctype", "html"} & html_signature:
        raise ValueError(
            "The uploaded file is HTML, not retail CSV data. "
            "This usually happens when a webpage was saved or renamed as .csv. "
            "Export the source table again as a real CSV file and re-upload it."
        )

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        available = ", ".join(map(str, df.columns[:12]))
        raise ValueError(
            f"Retail data is missing required columns: {', '.join(missing_columns)}. "
            f"Detected columns: {available}"
        )

    ingestion_summary = {
        "source": source_name,
        "rows_loaded": int(len(df)),
        "columns_loaded": int(len(df.columns)),
        "required_columns_ok": len(missing_columns) == 0,
        "missing_columns": missing_columns,
        "encoding_used": encoding_used,
        "delimiter_used": delimiter_used,
    }
    return df, ingestion_summary


def clean_retail_data(df: pd.DataFrame) -> tuple[pd.DataFrame, Dict[str, float]]:
    data = df.copy()
    original_rows = len(data)

    data["InvoiceDate"] = pd.to_datetime(
        data["InvoiceDate"], dayfirst=True, errors="coerce"
    )
    data["Quantity"] = pd.to_numeric(data["Quantity"], errors="coerce")
    data["UnitPrice"] = pd.to_numeric(data["UnitPrice"], errors="coerce")
    data["CustomerID"] = pd.to_numeric(data["CustomerID"], errors="coerce")
    data["Description"] = data["Description"].fillna("Unknown item")
    data["Country"] = data["Country"].fillna("Unknown")
    data["Invoice"] = data["Invoice"].astype(str).str.strip()

    invalid_dates = int(data["InvoiceDate"].isna().sum())
    missing_customers = int(data["CustomerID"].isna().sum())
    non_positive_rows = int(((data["Quantity"] <= 0) | (data["UnitPrice"] <= 0)).sum())
    cancelled_rows = int(data["Invoice"].str.startswith("C", na=False).sum())

    data = data.dropna(subset=["InvoiceDate", "CustomerID", "Quantity", "UnitPrice"])
    data = data[(data["Quantity"] > 0) & (data["UnitPrice"] > 0)]
    data = data[~data["Invoice"].str.startswith("C", na=False)]

    data["CustomerID"] = data["CustomerID"].astype("int64")
    data["Revenue"] = data["Quantity"] * data["UnitPrice"]
    data["OrderDate"] = data["InvoiceDate"].dt.normalize()
    data["Month"] = data["InvoiceDate"].dt.to_period("M").dt.to_timestamp()
    data["Week"] = data["InvoiceDate"].dt.to_period("W").dt.start_time
    data["DayName"] = data["InvoiceDate"].dt.day_name()
    data["Hour"] = data["InvoiceDate"].dt.hour
    data["BasketSize"] = data.groupby("Invoice")["Quantity"].transform("sum")

    cleaning_summary = {
        "original_rows": float(original_rows),
        "clean_rows": float(len(data)),
        "removed_rows": float(original_rows - len(data)),
        "validity_rate": float((len(data) / max(original_rows, 1)) * 100),
        "invalid_dates": float(invalid_dates),
        "missing_customers": float(missing_customers),
        "non_positive_rows": float(non_positive_rows),
        "cancelled_rows": float(cancelled_rows),
    }
    return data, cleaning_summary


def engineer_customer_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "recency_days",
                "frequency",
                "total_quantity",
                "monetary",
                "avg_order_value",
                "active_months",
                "primary_country",
                "avg_units_per_order",
                "monetary_per_month",
                "customer_value_score",
            ]
        )

    snapshot_date = df["InvoiceDate"].max() + pd.Timedelta(days=1)
    customer_features = df.groupby("CustomerID").agg(
        recency_days=("InvoiceDate", lambda values: (snapshot_date - values.max()).days),
        frequency=("Invoice", "nunique"),
        total_quantity=("Quantity", "sum"),
        monetary=("Revenue", "sum"),
        avg_order_value=("Revenue", "mean"),
        active_months=("Month", "nunique"),
        primary_country=("Country", lambda values: values.mode().iat[0]),
    )
    customer_features["avg_units_per_order"] = (
        customer_features["total_quantity"] / customer_features["frequency"]
    )
    customer_features["monetary_per_month"] = (
        customer_features["monetary"] / customer_features["active_months"].clip(lower=1)
    )

    recency_score = (
        1 - customer_features["recency_days"] / max(customer_features["recency_days"].max(), 1)
    ) * 100
    frequency_score = (
        customer_features["frequency"] / max(customer_features["frequency"].max(), 1)
    ) * 100
    monetary_score = (
        customer_features["monetary"] / max(customer_features["monetary"].max(), 1)
    ) * 100
    customer_features["customer_value_score"] = (
        (0.3 * recency_score) + (0.3 * frequency_score) + (0.4 * monetary_score)
    ).round(1)
    return customer_features


def segment_customers(customer_features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if customer_features.empty:
        empty_summary = pd.DataFrame(
            columns=[
                "segment_id",
                "segment",
                "customers",
                "avg_recency",
                "avg_frequency",
                "avg_monetary",
                "avg_order_value",
                "revenue_contribution_pct",
            ]
        )
        return customer_features.copy(), empty_summary

    if len(customer_features) < 3:
        enriched = customer_features.copy()
        enriched["segment_id"] = 0
        enriched["segment"] = "Regular"
        summary = pd.DataFrame(
            [
                {
                    "segment_id": 0,
                    "segment": "Regular",
                    "customers": len(enriched),
                    "avg_recency": float(enriched["recency_days"].mean()),
                    "avg_frequency": float(enriched["frequency"].mean()),
                    "avg_monetary": float(enriched["monetary"].mean()),
                    "avg_order_value": float(enriched["avg_order_value"].mean()),
                    "revenue_contribution_pct": 100.0,
                }
            ]
        )
        return enriched, summary

    feature_columns = [
        "recency_days",
        "frequency",
        "monetary",
        "avg_order_value",
        "avg_units_per_order",
        "monetary_per_month",
        "customer_value_score",
    ]
    scaled = StandardScaler().fit_transform(customer_features[feature_columns])

    model = KMeans(n_clusters=3, random_state=42, n_init=10)
    enriched = customer_features.copy()
    enriched["segment_id"] = model.fit_predict(scaled)

    summary = enriched.groupby("segment_id").agg(
        customers=("segment_id", "size"),
        avg_recency=("recency_days", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean"),
        avg_order_value=("avg_order_value", "mean"),
    )
    summary["rank_score"] = (
        summary["avg_monetary"].rank(method="dense", ascending=False)
        + summary["avg_frequency"].rank(method="dense", ascending=False)
        + summary["avg_recency"].rank(method="dense", ascending=True)
    )

    best_segment = int(summary["rank_score"].idxmin())
    weakest_segment = int(summary["rank_score"].idxmax())
    segment_labels = {}
    for segment_id in summary.index:
        if segment_id == best_segment:
            segment_labels[segment_id] = "VIP"
        elif segment_id == weakest_segment:
            segment_labels[segment_id] = "Low engagement"
        else:
            segment_labels[segment_id] = "Regular"

    enriched["segment"] = enriched["segment_id"].map(segment_labels)
    segment_revenue = enriched.groupby("segment_id")["monetary"].sum()
    total_revenue = float(segment_revenue.sum()) or 1.0
    summary["revenue_contribution_pct"] = (
        summary.index.to_series().map(segment_revenue).fillna(0.0) / total_revenue * 100
    )
    summary["segment"] = summary.index.map(segment_labels)
    summary = summary.sort_values("avg_monetary", ascending=False).reset_index()
    return enriched, summary


def build_daily_metrics(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "revenue",
                "orders",
                "customers",
                "units",
                "avg_order_value",
                "revenue_7d_ma",
                "order_7d_ma",
                "revenue_change_pct",
                "aov_change_pct",
                "revenue_volatility",
            ]
        )

    daily = df.groupby("OrderDate").agg(
        revenue=("Revenue", "sum"),
        orders=("Invoice", "nunique"),
        customers=("CustomerID", "nunique"),
        units=("Quantity", "sum"),
    )
    daily["avg_order_value"] = daily["revenue"] / daily["orders"].clip(lower=1)
    daily["revenue_7d_ma"] = daily["revenue"].rolling(7, min_periods=1).mean()
    daily["order_7d_ma"] = daily["orders"].rolling(7, min_periods=1).mean()
    daily["revenue_change_pct"] = (
        daily["revenue"].pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    )
    daily["aov_change_pct"] = (
        daily["avg_order_value"].pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    )
    daily["revenue_volatility"] = daily["revenue"].rolling(14, min_periods=2).std().fillna(0.0)
    daily.index = pd.DatetimeIndex(daily.index)
    return daily


def _fit_arima(series: pd.Series, periods: int) -> np.ndarray:
    if len(series) < 21:
        baseline = float(series.tail(min(7, len(series))).mean()) if len(series) else 0.0
        return np.repeat(baseline, periods)

    try:
        model = ARIMA(series, order=(2, 1, 2))
        fitted = model.fit()
        return np.asarray(fitted.forecast(steps=periods), dtype=float)
    except Exception:
        return np.repeat(float(series.tail(14).mean()), periods)


def evaluate_forecast_accuracy(daily_metrics: pd.DataFrame, horizon: int = 30) -> Dict[str, float]:
    if daily_metrics.empty or len(daily_metrics) < 45:
        return {
            "rmse": float("nan"),
            "mape": float("nan"),
            "forecast_reliability_score": 50.0,
            "evaluation_window": 0.0,
        }

    revenue_series = daily_metrics["revenue"].asfreq("D", fill_value=0.0)
    evaluation_window = min(horizon, max(len(revenue_series) // 5, 7))
    train = revenue_series.iloc[:-evaluation_window]
    actual = revenue_series.iloc[-evaluation_window:]
    predicted = _fit_arima(train, evaluation_window)

    rmse = float(np.sqrt(np.mean((actual.to_numpy() - predicted) ** 2)))
    safe_actual = np.where(actual.to_numpy() == 0, np.nan, actual.to_numpy())
    mape = float(np.nanmean(np.abs((actual.to_numpy() - predicted) / safe_actual)) * 100)
    mean_revenue = float(max(actual.mean(), 1.0))
    reliability_score = float(np.clip(100 - (rmse / mean_revenue) * 100, 0, 100))

    return {
        "rmse": rmse,
        "mape": 0.0 if np.isnan(mape) else mape,
        "forecast_reliability_score": reliability_score,
        "evaluation_window": float(evaluation_window),
    }


def forecast_demand(
    daily_metrics: pd.DataFrame, periods: int = 30, rmse: float | None = None
) -> pd.DataFrame:
    if daily_metrics.empty:
        forecast_index = pd.date_range(pd.Timestamp.today().normalize(), periods=periods, freq="D")
        empty_forecast = pd.DataFrame({"forecast_revenue": np.zeros(periods)}, index=forecast_index)
        empty_forecast.index.name = "OrderDate"
        empty_forecast["forecast_lower"] = 0.0
        empty_forecast["forecast_upper"] = 0.0
        return empty_forecast

    revenue_series = daily_metrics["revenue"].asfreq("D", fill_value=0.0)
    forecast_values = _fit_arima(revenue_series, periods)
    forecast_index = pd.date_range(
        revenue_series.index.max() + pd.Timedelta(days=1), periods=periods, freq="D"
    )
    forecast = pd.DataFrame(
        {"forecast_revenue": np.clip(forecast_values, 0, None)},
        index=forecast_index,
    )
    forecast.index.name = "OrderDate"
    interval = float(rmse) if rmse and not np.isnan(rmse) else max(float(revenue_series.std()), 1.0)
    forecast["forecast_lower"] = np.clip(forecast["forecast_revenue"] - interval, 0, None)
    forecast["forecast_upper"] = forecast["forecast_revenue"] + interval
    return forecast


def detect_anomalies(daily_metrics: pd.DataFrame) -> pd.DataFrame:
    if daily_metrics.empty:
        return pd.DataFrame(
            columns=[
                "OrderDate",
                "revenue",
                "orders",
                "customers",
                "units",
                "avg_order_value",
                "revenue_7d_ma",
                "order_7d_ma",
                "revenue_change_pct",
                "aov_change_pct",
                "revenue_volatility",
                "revenue_zscore",
                "aov_zscore",
                "is_revenue_anomaly",
                "is_aov_anomaly",
                "anomaly_type",
                "severity",
            ]
        )

    anomalies = daily_metrics.reset_index().copy()
    revenue_mean = float(anomalies["revenue"].mean())
    revenue_std = float(anomalies["revenue"].std(ddof=0) or 1.0)
    aov_mean = float(anomalies["avg_order_value"].mean())
    aov_std = float(anomalies["avg_order_value"].std(ddof=0) or 1.0)

    anomalies["revenue_zscore"] = (anomalies["revenue"] - revenue_mean) / revenue_std
    anomalies["aov_zscore"] = (anomalies["avg_order_value"] - aov_mean) / aov_std
    anomalies["is_revenue_anomaly"] = anomalies["revenue_zscore"].abs() > 2.0
    anomalies["is_aov_anomaly"] = anomalies["aov_zscore"].abs() > 2.0

    flagged = anomalies.loc[
        anomalies["is_revenue_anomaly"] | anomalies["is_aov_anomaly"]
    ].copy()
    flagged["anomaly_type"] = np.where(
        flagged["is_revenue_anomaly"] & flagged["is_aov_anomaly"],
        "Revenue and basket mix",
        np.where(flagged["is_revenue_anomaly"], "Revenue swing", "Basket value swing"),
    )
    flagged["severity"] = flagged[["revenue_zscore", "aov_zscore"]].abs().max(axis=1).round(2)
    return flagged.sort_values("severity", ascending=False)


def summarize_countries(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Country", "revenue", "orders", "customers", "avg_order_value"])

    country_summary = (
        df.groupby("Country")
        .agg(
            revenue=("Revenue", "sum"),
            orders=("Invoice", "nunique"),
            customers=("CustomerID", "nunique"),
        )
        .sort_values("revenue", ascending=False)
        .head(10)
        .reset_index()
    )
    country_summary["avg_order_value"] = (
        country_summary["revenue"] / country_summary["orders"].clip(lower=1)
    )
    return country_summary


def build_conversion_funnel_proxy(clean_data: pd.DataFrame) -> pd.DataFrame:
    if clean_data.empty:
        return pd.DataFrame(
            [
                {"stage": "Visitors", "value": 0, "note": "Proxy requires digital event data for precision"},
                {"stage": "Product Views", "value": 0, "note": "Proxy requires digital event data for precision"},
                {"stage": "Cart", "value": 0, "note": "Proxy requires digital event data for precision"},
                {"stage": "Purchase", "value": 0, "note": "Observed completed orders"},
            ]
        )

    purchases = int(clean_data["Invoice"].nunique())
    carts = int(np.ceil(purchases / 0.68))
    product_views = int(np.ceil(carts / 0.34))
    visitors = int(np.ceil(product_views / 0.58))
    return pd.DataFrame(
        [
            {
                "stage": "Visitors",
                "value": visitors,
                "note": "Modeled proxy from purchase completions until digital event data is integrated",
            },
            {
                "stage": "Product Views",
                "value": product_views,
                "note": "Modeled proxy from purchase completions until digital event data is integrated",
            },
            {
                "stage": "Cart",
                "value": carts,
                "note": "Modeled proxy from purchase completions until digital event data is integrated",
            },
            {
                "stage": "Purchase",
                "value": purchases,
                "note": "Observed completed orders from the retail ledger",
            },
        ]
    )


def calculate_health_score(
    clean_data: pd.DataFrame,
    customer_features: pd.DataFrame,
    daily_metrics: pd.DataFrame,
    anomalies: pd.DataFrame,
    forecast_metrics: Dict[str, float],
) -> tuple[int, str, pd.DataFrame]:
    if clean_data.empty or customer_features.empty or daily_metrics.empty:
        components = pd.DataFrame(
            [
                {
                    "component": "Revenue stability",
                    "weight": 0.30,
                    "value": 0.0,
                    "score": 0.0,
                    "context": "No clean transactions available",
                },
                {
                    "component": "Forecast reliability",
                    "weight": 0.20,
                    "value": 0.0,
                    "score": 0.0,
                    "context": "No clean transactions available",
                },
                {
                    "component": "Customer retention",
                    "weight": 0.25,
                    "value": 0.0,
                    "score": 0.0,
                    "context": "No clean transactions available",
                },
                {
                    "component": "Sales volatility",
                    "weight": 0.25,
                    "value": 0.0,
                    "score": 0.0,
                    "context": "No clean transactions available",
                },
            ]
        )
        return 0, "Offline", components

    recent = daily_metrics.tail(min(30, len(daily_metrics)))
    revenue_cv = float(recent["revenue"].std(ddof=0) / max(recent["revenue"].mean(), 1.0))
    revenue_stability_score = float(np.clip(100 - (revenue_cv * 100), 0, 100))
    repeat_customer_rate = float((customer_features["frequency"] > 1).mean() * 100)
    volatility_index = float(recent["revenue_change_pct"].abs().mean() * 100)
    sales_volatility_score = float(np.clip(100 - volatility_index, 0, 100))
    forecast_score = float(np.clip(forecast_metrics["forecast_reliability_score"], 0, 100))

    components = pd.DataFrame(
        [
            {
                "component": "Revenue stability",
                "weight": 0.30,
                "value": revenue_cv,
                "score": revenue_stability_score,
                "context": "Coefficient of variation of recent daily revenue",
            },
            {
                "component": "Forecast reliability",
                "weight": 0.20,
                "value": forecast_metrics["rmse"],
                "score": forecast_score,
                "context": "Backtested ARIMA forecast reliability",
            },
            {
                "component": "Customer retention",
                "weight": 0.25,
                "value": repeat_customer_rate,
                "score": repeat_customer_rate,
                "context": "Customers placing more than one order",
            },
            {
                "component": "Sales volatility",
                "weight": 0.25,
                "value": volatility_index,
                "score": sales_volatility_score,
                "context": "Average absolute day-to-day revenue change",
            },
        ]
    )

    health_score = int(round(np.average(components["score"], weights=components["weight"])))
    if health_score >= 80:
        health_status = "Healthy"
    elif health_score >= 60:
        health_status = "Stable"
    else:
        health_status = "At Risk"
    return health_score, health_status, components


def build_segment_distribution(customer_features: pd.DataFrame) -> pd.DataFrame:
    if customer_features.empty:
        return pd.DataFrame(columns=["segment", "customers", "revenue"])

    return (
        customer_features.groupby("segment")
        .agg(customers=("segment", "size"), revenue=("monetary", "sum"))
        .reset_index()
        .sort_values("revenue", ascending=False)
    )


def generate_recommendations(
    daily_metrics: pd.DataFrame,
    forecast: pd.DataFrame,
    segment_summary: pd.DataFrame,
    anomalies: pd.DataFrame,
    health_score: int,
) -> List[Dict[str, str]]:
    if daily_metrics.empty:
        return [
            {
                "title": "Load valid retail transactions",
                "priority": "High",
                "action": "No clean transactions were available for modeling. Check the input schema, transaction quality, and ingestion pipeline before using RetailOS decisions.",
            }
        ]

    recommendations: List[Dict[str, str]] = []
    recent_revenue = float(daily_metrics["revenue"].tail(14).mean())
    forecast_revenue = float(forecast["forecast_revenue"].head(14).mean())

    if forecast_revenue < recent_revenue * 0.97:
        recommendations.append(
            {
                "title": "Protect near-term demand",
                "priority": "High",
                "action": "Increase promotional pressure on Regular and Low engagement cohorts before forecasted sales soften over the next two weeks.",
            }
        )
    else:
        recommendations.append(
            {
                "title": "Scale into forecast momentum",
                "priority": "Medium",
                "action": "Increase inventory coverage and staffing on the strongest trading windows because the next 30-day forecast is holding above the recent run-rate.",
            }
        )

    vip_segment = segment_summary.loc[segment_summary["segment"] == "VIP"]
    low_segment = segment_summary.loc[segment_summary["segment"] == "Low engagement"]
    if not vip_segment.empty and not low_segment.empty:
        recommendations.append(
            {
                "title": "Protect VIP revenue share",
                "priority": "High",
                "action": (
                    f"VIP customers contribute materially more revenue than Low engagement customers. "
                    "Use loyalty or early-access campaigns to preserve high-value retention."
                ),
            }
        )

    if not anomalies.empty:
        top_anomaly = anomalies.iloc[0]
        recommendations.append(
            {
                "title": "Investigate anomaly root cause",
                "priority": "Medium",
                "action": (
                    f"{top_anomaly['anomaly_type']} was detected on "
                    f"{pd.to_datetime(top_anomaly['OrderDate']).date()}. Review campaigns, stockouts, returns, and manual price overrides."
                ),
            }
        )

    if health_score < 60:
        recommendations.append(
            {
                "title": "Stabilize retail operations",
                "priority": "High",
                "action": "Focus the next operating cycle on retention, forecast monitoring, and volatility reduction before expansion bets.",
            }
        )
    else:
        recommendations.append(
            {
                "title": "Expand with measured confidence",
                "priority": "Medium",
                "action": "Retail health is supportive of targeted growth tests in top geographies and stronger customer cohorts.",
            }
        )

    return recommendations[:4]


def compute_kpis(
    clean_data: pd.DataFrame,
    daily_metrics: pd.DataFrame,
    customer_features: pd.DataFrame,
    health_score: int,
) -> Dict[str, float]:
    total_revenue = float(clean_data["Revenue"].sum()) if not clean_data.empty else 0.0
    total_orders = float(clean_data["Invoice"].nunique()) if not clean_data.empty else 0.0
    total_customers = float(clean_data["CustomerID"].nunique()) if not clean_data.empty else 0.0
    avg_order_value = total_revenue / max(total_orders, 1.0)
    repeat_rate = (
        float((customer_features["frequency"] > 1).mean() * 100)
        if not customer_features.empty
        else 0.0
    )
    recent_daily_revenue = (
        float(daily_metrics["revenue"].tail(30).mean()) if not daily_metrics.empty else 0.0
    )
    recent_week = float(daily_metrics["revenue"].tail(7).sum()) if not daily_metrics.empty else 0.0
    previous_week = (
        float(daily_metrics["revenue"].iloc[-14:-7].sum())
        if len(daily_metrics) >= 14
        else recent_week
    )
    weekly_growth = ((recent_week - previous_week) / max(previous_week, 1.0)) * 100

    return {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "total_customers": total_customers,
        "avg_order_value": avg_order_value,
        "repeat_rate": repeat_rate,
        "recent_daily_revenue": recent_daily_revenue,
        "weekly_growth": weekly_growth,
        "health_score": float(health_score),
    }


def run_retail_intelligence(source) -> RetailIntelligenceArtifacts:
    refreshed_at = pd.Timestamp.now(tz="UTC")
    raw_data, ingestion_summary = load_retail_data(source)
    clean_data, cleaning_summary = clean_retail_data(raw_data)
    customer_features = engineer_customer_features(clean_data)
    customer_features, segment_summary = segment_customers(customer_features)
    daily_metrics = build_daily_metrics(clean_data)
    forecast_metrics = evaluate_forecast_accuracy(daily_metrics)
    forecast = forecast_demand(daily_metrics, rmse=forecast_metrics["rmse"])
    anomalies = detect_anomalies(daily_metrics)
    country_summary = summarize_countries(clean_data)
    funnel_proxy = build_conversion_funnel_proxy(clean_data)
    health_score, health_status, health_components = calculate_health_score(
        clean_data,
        customer_features,
        daily_metrics,
        anomalies,
        forecast_metrics,
    )
    recommendations = generate_recommendations(
        daily_metrics, forecast, segment_summary, anomalies, health_score
    )
    kpis = compute_kpis(clean_data, daily_metrics, customer_features, health_score)
    ingestion_summary["date_min"] = (
        clean_data["OrderDate"].min().date().isoformat() if not clean_data.empty else None
    )
    ingestion_summary["date_max"] = (
        clean_data["OrderDate"].max().date().isoformat() if not clean_data.empty else None
    )
    ingestion_summary["countries"] = int(clean_data["Country"].nunique()) if not clean_data.empty else 0

    return RetailIntelligenceArtifacts(
        raw_data=raw_data,
        clean_data=clean_data,
        customer_features=customer_features,
        segment_summary=segment_summary,
        daily_metrics=daily_metrics,
        forecast=forecast,
        anomalies=anomalies,
        country_summary=country_summary,
        health_components=health_components,
        recommendations=recommendations,
        kpis=kpis,
        cleaning_summary=cleaning_summary,
        ingestion_summary=ingestion_summary,
        forecast_metrics=forecast_metrics,
        funnel_proxy=funnel_proxy,
        health_score=health_score,
        health_status=health_status,
        refreshed_at=refreshed_at,
    )
