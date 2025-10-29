-- Migration: Create excel_exports table
-- Purpose: Track Excel export files with metadata for reconciliation
-- Author: Claude Code
-- Date: 2025-10-29

-- Create excel_exports table
CREATE TABLE IF NOT EXISTS excel_exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    batch_id UUID REFERENCES batches(id) ON DELETE SET NULL,
    result_id UUID REFERENCES results(id) ON DELETE SET NULL,

    -- File information
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(500) NOT NULL UNIQUE,
    document_type VARCHAR(50) NOT NULL CHECK (document_type IN ('faktur_pajak', 'rekening_koran', 'pph21', 'pph23', 'batch', 'unknown')),

    -- File metadata
    row_count INTEGER DEFAULT 0,
    file_size BIGINT DEFAULT 0,
    sheet_names JSONB,

    -- Document-specific metadata
    date_range JSONB, -- {start: '2021-01-01', end: '2021-12-31'}
    bank_name VARCHAR(100),
    account_number VARCHAR(100),
    account_holder VARCHAR(200),

    -- Reconciliation tracking
    is_reconciled BOOLEAN DEFAULT FALSE,
    reconciliation_id UUID,
    reconciled_at TIMESTAMP,

    -- Audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    CONSTRAINT excel_exports_pkey PRIMARY KEY (id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_excel_exports_user_id ON excel_exports(user_id);
CREATE INDEX IF NOT EXISTS idx_excel_exports_batch_id ON excel_exports(batch_id);
CREATE INDEX IF NOT EXISTS idx_excel_exports_result_id ON excel_exports(result_id);
CREATE INDEX IF NOT EXISTS idx_excel_exports_document_type ON excel_exports(document_type);
CREATE INDEX IF NOT EXISTS idx_excel_exports_created_at ON excel_exports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_excel_exports_is_reconciled ON excel_exports(is_reconciled);
CREATE INDEX IF NOT EXISTS idx_excel_exports_filepath ON excel_exports(filepath);

-- Create trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_excel_exports_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER excel_exports_updated_at_trigger
    BEFORE UPDATE ON excel_exports
    FOR EACH ROW
    EXECUTE FUNCTION update_excel_exports_updated_at();

-- Add comment to table
COMMENT ON TABLE excel_exports IS 'Tracks Excel export files generated from OCR scans with metadata for reconciliation';
COMMENT ON COLUMN excel_exports.document_type IS 'Type of document: faktur_pajak, rekening_koran, pph21, pph23, batch, unknown';
COMMENT ON COLUMN excel_exports.date_range IS 'JSON object with start and end dates for the document period';
COMMENT ON COLUMN excel_exports.is_reconciled IS 'Flag indicating if this Excel has been used in reconciliation';
COMMENT ON COLUMN excel_exports.reconciliation_id IS 'UUID of the reconciliation record if reconciled';
