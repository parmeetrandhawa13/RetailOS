from src.retail_intelligence import clean_retail_data, load_retail_data


def load_and_clean_data(path):
    raw_data = load_retail_data(path)
    clean_data, _ = clean_retail_data(raw_data)
    return clean_data
