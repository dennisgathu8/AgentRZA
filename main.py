import argparse
import asyncio
from src.graph import run_pipeline

def main():
    """
    Zero-Trust Football Gravity Pipeline
    Produces an encrypted DuckDB Parquet containing enriched xG models.
    """
    parser = argparse.ArgumentParser(description="Run the secure Football Gravity Agent Pipeline")
    parser.add_argument("--date", type=str, required=True, help="Target date to run pipeline for (e.g., 'today' or 'YYYY-MM-DD')")
    args = parser.parse_args()
    
    print(f"[*] Initializing Football Gravity Pipeline for target date: {args.date}")
    
    # Run the compiled LangGraph workflow
    final_state = asyncio.run(run_pipeline(args.date))
    
    print("[*] Pipeline Execution Complete.")
    print(f"[*] Final Status: {final_state['pipeline_status']}")
    if final_state['errors']:
        print("[!] Encountered Errors during run:")
        for err in final_state['errors']:
            print(f"    - {err}")

if __name__ == "__main__":
    main()
