#!/usr/bin/env python3
import asyncio
import logging
from core.scanner_core import QuantumScanner

async def main():
    logging.basicConfig(level=logging.INFO)
    scanner = QuantumScanner(dry_run=False)
    await scanner.run()

if __name__ == "__main__":
    asyncio.run(main())
