#!/usr/bin/env python3
"""
Run the OCPP test server (CSMS).
"""

import asyncio
import argparse
from ocpp_fuzzing.server import main, DEFAULT_HOST, DEFAULT_PORT

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run OCPP 1.6 CSMS test server")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Listen port (default: 9000)")
    args = parser.parse_args()

    asyncio.run(main(host=args.host, port=args.port))