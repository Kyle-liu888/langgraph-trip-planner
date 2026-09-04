"""Psycopg async connections require SelectorEventLoop on Windows."""
import asyncio


def selector_factory():
    return asyncio.SelectorEventLoop()
