from src.retail_intelligence import engineer_customer_features, segment_customers


def perform_rfm_segmentation(df):
    customer_features = engineer_customer_features(df)
    segmented_customers, _ = segment_customers(customer_features)
    return segmented_customers
