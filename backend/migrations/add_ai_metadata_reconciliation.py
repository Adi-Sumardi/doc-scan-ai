"""
Database Migration: Add AI Metadata to Reconciliation Tables
Version: 2.0.0
Date: 2025-10-18

Adds AI processing metadata fields to support dual AI routing:
- TaxInvoice: ai_model_used, extraction_confidence
- BankTransaction: extracted_vendor_name, extracted_invoice_number, ai_model_used, extraction_confidence
"""

import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from database import engine, SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_up():
    """Apply migration: Add AI metadata columns"""

    db = SessionLocal()

    try:
        logger.info("🚀 Starting migration: Add AI metadata to reconciliation tables")

        # Migration for TaxInvoice table
        logger.info("📊 Migrating tax_invoices table...")

        # Helper function to check if column exists
        def column_exists(table_name, column_name):
            result = db.execute(text(f"""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = '{table_name}'
                AND COLUMN_NAME = '{column_name}'
            """)).fetchone()
            return result.count > 0

        migrations = [
            # TaxInvoice: Add AI metadata
            ("tax_invoices", "ai_model_used", "ALTER TABLE tax_invoices ADD COLUMN ai_model_used VARCHAR(50) DEFAULT 'gpt-4o'"),
            ("tax_invoices", "extraction_confidence", "ALTER TABLE tax_invoices ADD COLUMN extraction_confidence FLOAT"),

            # BankTransaction: Add AI extracted fields
            ("bank_transactions", "extracted_vendor_name", "ALTER TABLE bank_transactions ADD COLUMN extracted_vendor_name VARCHAR(255)"),
            ("bank_transactions", "extracted_invoice_number", "ALTER TABLE bank_transactions ADD COLUMN extracted_invoice_number VARCHAR(100)"),
            ("bank_transactions", "ai_model_used", "ALTER TABLE bank_transactions ADD COLUMN ai_model_used VARCHAR(50) DEFAULT 'claude-sonnet-4'"),
            ("bank_transactions", "extraction_confidence", "ALTER TABLE bank_transactions ADD COLUMN extraction_confidence FLOAT"),
        ]

        # Execute migrations
        for table_name, column_name, sql in migrations:
            if not column_exists(table_name, column_name):
                logger.info(f"  Adding {column_name} to {table_name}...")
                db.execute(text(sql))
                db.commit()
            else:
                logger.info(f"  ⏭️  Column {column_name} already exists in {table_name}")

        logger.info("✅ Column additions completed")

        # Add indexes for better query performance
        indexes = [
            ("idx_tax_invoices_ai_model", "tax_invoices", "ai_model_used"),
            ("idx_bank_transactions_extracted_vendor", "bank_transactions", "extracted_vendor_name"),
            ("idx_bank_transactions_ai_model", "bank_transactions", "ai_model_used"),
        ]

        # Execute indexes
        logger.info("📊 Creating indexes...")
        for index_name, table_name, column_name in indexes:
            # Check if index exists
            result = db.execute(text(f"""
                SELECT COUNT(*) as count
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = '{table_name}'
                AND INDEX_NAME = '{index_name}'
            """)).fetchone()

            if result.count == 0:
                logger.info(f"  Creating index {index_name}...")
                db.execute(text(f"CREATE INDEX {index_name} ON {table_name}({column_name})"))
                db.commit()
            else:
                logger.info(f"  ⏭️  Index {index_name} already exists")

        logger.info("✅ Index creation completed")

        # Verify migration
        logger.info("🔍 Verifying migration...")
        result = db.execute(text("""
            SELECT
                COUNT(*) as invoice_cols
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'tax_invoices'
            AND COLUMN_NAME IN ('ai_model_used', 'extraction_confidence')
        """)).fetchone()

        if result.invoice_cols == 2:
            logger.info("✅ TaxInvoice columns verified")
        else:
            logger.warning(f"⚠️  Expected 2 columns, found {result.invoice_cols}")

        result = db.execute(text("""
            SELECT
                COUNT(*) as transaction_cols
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'bank_transactions'
            AND COLUMN_NAME IN ('extracted_vendor_name', 'extracted_invoice_number', 'ai_model_used', 'extraction_confidence')
        """)).fetchone()

        if result.transaction_cols == 4:
            logger.info("✅ BankTransaction columns verified")
        else:
            logger.warning(f"⚠️  Expected 4 columns, found {result.transaction_cols}")

        logger.info("🎉 Migration completed successfully!")
        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def migrate_down():
    """Rollback migration: Remove AI metadata columns"""

    db = SessionLocal()

    try:
        logger.info("🔄 Rolling back migration: Remove AI metadata columns")

        rollbacks = [
            # TaxInvoice: Remove AI metadata
            "ALTER TABLE tax_invoices DROP COLUMN IF EXISTS ai_model_used",
            "ALTER TABLE tax_invoices DROP COLUMN IF EXISTS extraction_confidence",

            # BankTransaction: Remove AI extracted fields
            "ALTER TABLE bank_transactions DROP COLUMN IF EXISTS extracted_vendor_name",
            "ALTER TABLE bank_transactions DROP COLUMN IF EXISTS extracted_invoice_number",
            "ALTER TABLE bank_transactions DROP COLUMN IF EXISTS ai_model_used",
            "ALTER TABLE bank_transactions DROP COLUMN IF EXISTS extraction_confidence",
        ]

        for sql in rollbacks:
            logger.info(f"  Executing: {sql}")
            db.execute(text(sql))
            db.commit()

        logger.info("✅ Rollback completed successfully!")
        return True

    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database migration for AI metadata")
    parser.add_argument(
        "action",
        choices=["up", "down", "status"],
        help="Migration action: up (apply), down (rollback), status (check)"
    )

    args = parser.parse_args()

    if args.action == "up":
        migrate_up()
    elif args.action == "down":
        confirm = input("⚠️  Are you sure you want to rollback? This will remove AI metadata columns. (yes/no): ")
        if confirm.lower() == "yes":
            migrate_down()
        else:
            logger.info("Rollback cancelled")
    elif args.action == "status":
        db = SessionLocal()
        try:
            # Check TaxInvoice columns
            result = db.execute(text("""
                SELECT COLUMN_NAME, DATA_TYPE, COLUMN_DEFAULT
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'tax_invoices'
                AND COLUMN_NAME IN ('ai_model_used', 'extraction_confidence')
                ORDER BY COLUMN_NAME
            """)).fetchall()

            logger.info("📊 TaxInvoice AI columns:")
            for row in result:
                logger.info(f"  - {row.COLUMN_NAME} ({row.DATA_TYPE}): {row.COLUMN_DEFAULT}")

            # Check BankTransaction columns
            result = db.execute(text("""
                SELECT COLUMN_NAME, DATA_TYPE, COLUMN_DEFAULT
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'bank_transactions'
                AND COLUMN_NAME IN ('extracted_vendor_name', 'extracted_invoice_number', 'ai_model_used', 'extraction_confidence')
                ORDER BY COLUMN_NAME
            """)).fetchall()

            logger.info("📊 BankTransaction AI columns:")
            for row in result:
                logger.info(f"  - {row.COLUMN_NAME} ({row.DATA_TYPE}): {row.COLUMN_DEFAULT}")

        finally:
            db.close()
