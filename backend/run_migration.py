#!/usr/bin/env python3
"""
Run database migration for excel_exports table
"""
import asyncpg
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def run_migration():
    # Database connection
    conn = await asyncpg.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME', 'doc_scan_ai'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD')
    )

    print('🔧 Running migration: 004_create_excel_exports_table.sql')
    print('=' * 80)

    # Read migration file
    with open('migrations/004_create_excel_exports_table.sql', 'r') as f:
        migration_sql = f.read()

    try:
        await conn.execute(migration_sql)
        print('✅ Migration completed successfully!')
    except Exception as e:
        print(f'❌ Migration failed: {e}')
        await conn.close()
        return

    # Verify table creation
    print('📊 Checking table...')
    columns = await conn.fetch("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'excel_exports'
        ORDER BY ordinal_position
    """)

    print(f'\n✅ Table excel_exports created with {len(columns)} columns:')
    for row in columns[:10]:
        print(f'   - {row["column_name"]}: {row["data_type"]}')
    if len(columns) > 10:
        print(f'   ... and {len(columns) - 10} more columns')

    await conn.close()
    print('\n' + '=' * 80)
    print('✅ Migration complete! Database ready for Excel exports tracking')

if __name__ == '__main__':
    asyncio.run(run_migration())
