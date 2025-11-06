#!/usr/bin/env python3
"""
Run database migration for PPN reconciliation tables
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

    print('🔧 Running migration: 005_create_ppn_reconciliation_tables.sql')
    print('=' * 80)

    # Read migration file
    with open('migrations/005_create_ppn_reconciliation_tables.sql', 'r') as f:
        migration_sql = f.read()

    try:
        await conn.execute(migration_sql)
        print('✅ Migration completed successfully!')
    except Exception as e:
        print(f'❌ Migration failed: {e}')
        await conn.close()
        return

    # Verify table creation
    print('📊 Checking tables...')
    tables = ['ppn_projects', 'ppn_data_sources', 'ppn_point_a', 'ppn_point_b', 'ppn_point_c', 'ppn_point_e']

    for table_name in tables:
        columns = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = $1
            ORDER BY ordinal_position
        """, table_name)

        if columns:
            print(f'\n✅ Table {table_name} created with {len(columns)} columns:')
            for row in columns[:5]:
                print(f'   - {row["column_name"]}: {row["data_type"]}')
            if len(columns) > 5:
                print(f'   ... and {len(columns) - 5} more columns')
        else:
            print(f'\n❌ Table {table_name} not found!')

    await conn.close()
    print('\n' + '=' * 80)
    print('✅ Migration complete! Database ready for PPN reconciliation')

if __name__ == '__main__':
    asyncio.run(run_migration())
