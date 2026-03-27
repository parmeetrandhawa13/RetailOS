from src.retail_intelligence import build_daily_metrics, forecast_demand as forecast_revenue


def forecast_demand(df):
    daily_metrics = build_daily_metrics(df)
    forecast = forecast_revenue(daily_metrics)
    return daily_metrics["revenue"], forecast["forecast_revenue"]
