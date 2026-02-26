#!/usr/bin/env python3
import asyncio
import asyncpg
import os

DATABASE_URL = os.getenv('DATABASE_URL')

async def check():
    conn = await asyncpg.connect(DATABASE_URL)
    tables = await conn.fetch('SELECT table_name FROM information_schema.tables WHERE table_schema = $1 ORDER BY table_name', 'public')
    print('Tablas existentes en Railway:')
    for t in tables:
        print(f'  - {t[0]}')
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check())
