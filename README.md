# RetailOS - Retail Intelligence Dashboard

A comprehensive retail analytics dashboard built with Streamlit, featuring customer segmentation, demand forecasting, anomaly detection, and business intelligence insights.

## Features

- **Customer Segmentation**: K-means clustering for customer behavior analysis
- **Demand Forecasting**: ARIMA-based revenue forecasting
- **Anomaly Detection**: Statistical outlier detection for business metrics
- **Health Scoring**: Comprehensive business health assessment
- **Interactive Dashboard**: Modern UI with filtering and visualization
- **Performance Optimized**: Fast loading with intelligent caching

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/parmeetrandhawa13/RetailOS.git
   cd RetailOS
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the dashboard:**
   ```bash
   streamlit run dashboard_app.py
   ```

4. **Login with default credentials:**
   - Username: `admin`
   - Password: `ChangeMeNow123`

## Data Requirements

Upload a CSV file with the following columns:
- Invoice
- StockCode
- Description
- Quantity
- InvoiceDate
- Price
- CustomerID
- Country

## Performance

- **First load**: 2-3 seconds (optimized with data sampling)
- **Subsequent loads**: <100ms (cached)
- **Data processing**: Handles 500K+ transactions efficiently

## Documentation

- [QUICK_START.md](QUICK_START.md) - Quick setup guide
- [PERFORMANCE.md](PERFORMANCE.md) - Performance optimization details
- [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment guide

## Tech Stack

- **Frontend**: Streamlit
- **Data Processing**: pandas, numpy
- **Machine Learning**: scikit-learn, statsmodels
- **Visualization**: Altair
- **Authentication**: Local + Google OAuth support

## License

MIT License - see LICENSE file for details.