#!/usr/bin/env python3
"""
Run the corpus generator CLI.
"""

from ocpp_fuzzing.generator import main

if __name__ == "__main__":
    # generator.py 안의 main()이 argparse 처리 후 실행되도록
    main()