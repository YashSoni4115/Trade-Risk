"""
TradeRisk Application Entry Point
===================================
Run the Flask API server.
"""

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.routes import create_app


def main():
    """Main entry point."""
    load_dotenv(Path(__file__).parent / ".env")
    # Get data directory from command line or use default
    data_dir = sys.argv[1] if len(sys.argv) > 1 else None
    
    print("=" * 60)
    print("TradeRisk Risk Engine API")
    print("=" * 60)
    print()
    
    # Create and run the app
    app = create_app(data_dir)
    
    print("Starting server on http://localhost:5001")
    print()
    print("Available endpoints:")
    print("  GET  /health              - Health check")
    print("  GET  /api/sectors         - List all sectors")
    print("  GET  /api/sector/<id>     - Get sector details")
    print("  GET  /api/baseline        - Get baseline risk scores")
    print("  POST /api/scenario        - Calculate scenario risk")
    print("  POST /api/compare         - Compare two scenarios")
    print("  GET  /api/actual-tariffs  - Risk using ACTUAL tariffs on Canada")
    print("  GET  /api/tariff-rates    - View actual tariff rates by sector")
    print("  GET  /api/partners        - List valid partners")
    print("  GET  /api/config          - Get engine configuration")
    print()
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5001, debug=False)


if __name__ == '__main__':
    main()
