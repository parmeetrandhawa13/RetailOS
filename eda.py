import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# -----------------------------
# 1. LOAD DATA
# -----------------------------
df = pd.read_csv("data/retail.csv", encoding="ISO-8859-1")

# Fix weird column name
df.columns = df.columns.str.replace("ï»¿Invoice", "InvoiceNo")

# -----------------------------
# 2. CLEAN DATA
# -----------------------------
df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'], dayfirst=True)

df = df.dropna(subset=['Customer ID'])
df = df[df['Quantity'] > 0]

# Create Revenue column
df['Revenue'] = df['Quantity'] * df['Price']

print("Total Revenue:", round(df['Revenue'].sum(), 2))
print("Total Customers:", df['Customer ID'].nunique())

# -----------------------------
# 3. MONTHLY SALES TREND
# -----------------------------
df['Month'] = df['InvoiceDate'].dt.to_period('M')
monthly_sales = df.groupby('Month')['Revenue'].sum()

plt.figure(figsize=(10,5))
monthly_sales.plot()
plt.title("Monthly Sales Trend")
plt.xlabel("Month")
plt.ylabel("Revenue")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# -----------------------------
# 4. RFM SEGMENTATION
# -----------------------------
snapshot_date = df['InvoiceDate'].max() + pd.Timedelta(days=1)

rfm = df.groupby('Customer ID').agg({
    'InvoiceDate': lambda x: (snapshot_date - x.max()).days,
    'InvoiceNo': 'count',
    'Revenue': 'sum'
})

rfm.columns = ['Recency', 'Frequency', 'Monetary']

print("\nRFM Table Sample:")
print(rfm.head())

# -----------------------------
# 5. SCALING
# -----------------------------
scaler = StandardScaler()
rfm_scaled = scaler.fit_transform(rfm)

# -----------------------------
# 6. KMEANS CLUSTERING
# -----------------------------
kmeans = KMeans(n_clusters=3, random_state=42)
rfm['Cluster'] = kmeans.fit_predict(rfm_scaled)

print("\nCluster Counts:")
print(rfm['Cluster'].value_counts())

# -----------------------------
# 7. CLUSTER SUMMARY
# -----------------------------
cluster_summary = rfm.groupby('Cluster').mean()

print("\nCluster Summary:")
print(cluster_summary)

# -----------------------------
# 8. VISUALIZE CLUSTERS
# -----------------------------
plt.figure(figsize=(8,5))
plt.scatter(rfm['Frequency'], rfm['Monetary'], c=rfm['Cluster'])
plt.title("Customer Segments")
plt.xlabel("Frequency")
plt.ylabel("Monetary")
plt.tight_layout()
plt.show()
# -----------------------------
# 9. DEMAND FORECASTING (ARIMA)
# -----------------------------
from statsmodels.tsa.arima.model import ARIMA

# Prepare daily revenue
daily_sales = df.groupby(df['InvoiceDate'].dt.date)['Revenue'].sum()
daily_sales = pd.Series(daily_sales)

print("\nTraining ARIMA model...")

# Train ARIMA model
model = ARIMA(daily_sales, order=(5,1,0))
model_fit = model.fit()

# Forecast next 30 days
forecast = model_fit.forecast(steps=30)

# Plot results
plt.figure(figsize=(10,5))
plt.plot(daily_sales.index, daily_sales, label="Actual Sales")
plt.plot(forecast.index, forecast, label="Forecast (Next 30 Days)")
plt.title("Demand Forecasting (ARIMA)")
plt.xlabel("Date")
plt.ylabel("Revenue")
plt.legend()
plt.tight_layout()
plt.show()