#!/usr/bin/env python3
"""
Performance test for dashboard loading speed.
Tests if load_artifacts achieves 2-3 second target.
"""
import time
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from retail_intelligence import run_retail_intelligence

def test_load_speed():
    """Test the load speed with the sample retail data."""
    data_path = Path(__file__).parent / "data" / "retail.csv"
    
    if not data_path.exists():
        print(f"❌ Data file not found: {data_path}")
        return False
    
    print(f"📊 Testing load speed with data from {data_path.name}...")
    print(f"📈 File size: {data_path.stat().st_size / 1024 / 1024:.1f} MB")
    print("-" * 60)
    
    try:
        start_time = time.perf_counter()
        artifacts = run_retail_intelligence(data_path)
        end_time = time.perf_counter()
        
        elapsed = end_time - start_time
        
        print(f"✅ Load completed in {elapsed:.2f} seconds")
        print("-" * 60)
        print(f"Target: 2-3 seconds")
        print(f"Status: {'✅ PASS' if 2 <= elapsed <= 3 else '⚠️  EXCEEDS TARGET' if elapsed > 3 else '✅ FASTER'}")
        print("-" * 60)
        
        # Summary stats
        print(f"Data Summary:")
        print(f"  • Rows loaded: {artifacts.ingestion_summary.get('original_rows', 'N/A')}")
        print(f"  • Rows after 12-month limit: {artifacts.ingestion_summary.get('rows_after_limit', 'N/A')}")
        print(f"  • Date range: {artifacts.ingestion_summary['date_min']} to {artifacts.ingestion_summary['date_max']}")
        print(f"  • Countries: {artifacts.ingestion_summary['countries']}")
        print(f"  • Customers: {len(artifacts.customer_features)}")
        print(f"  • Days with data: {len(artifacts.daily_metrics)}")
        
        return 2 <= elapsed <= 3
        
    except Exception as e:
        print(f"❌ Error during load: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_load_speed()
    sys.exit(0 if success else 1)
