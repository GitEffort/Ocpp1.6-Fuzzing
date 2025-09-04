#!/usr/bin/env python3
"""
Run the replay sender CLI.
"""

import asyncio
from ocpp_fuzzing.sender import main

if __name__ == "__main__":
    asyncio.run(main())