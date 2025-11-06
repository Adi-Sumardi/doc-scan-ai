-- Migration: Create PPN Reconciliation tables
-- Purpose: Support comprehensive PPN (tax) reconciliation workflow
-- Author: Claude Code
-- Date: 2025-11-06

-- ==================== PPN Projects Table ====================

CREATE TABLE IF NOT EXISTS ppn_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Project metadata
    name VARCHAR(255) NOT NULL,
    periode_start DATE NOT NULL,
    periode_end DATE NOT NULL,
    company_npwp VARCHAR(20) NOT NULL,

    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'in_progress', 'completed', 'archived')),

    -- Counts for each point
    point_a_count INTEGER DEFAULT 0,
    point_b_count INTEGER DEFAULT 0,
    point_c_count INTEGER DEFAULT 0,
    point_e_count INTEGER DEFAULT 0,

    -- Audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,

    -- Constraints
    CONSTRAINT ppn_projects_pkey PRIMARY KEY (id),
    CONSTRAINT valid_date_range CHECK (periode_end >= periode_start)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_ppn_projects_user_id ON ppn_projects(user_id);
CREATE INDEX IF NOT EXISTS idx_ppn_projects_status ON ppn_projects(status);
CREATE INDEX IF NOT EXISTS idx_ppn_projects_created_at ON ppn_projects(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ppn_projects_periode ON ppn_projects(periode_start, periode_end);

-- Add comments
COMMENT ON TABLE ppn_projects IS 'PPN reconciliation projects for managing tax document reconciliation';
COMMENT ON COLUMN ppn_projects.company_npwp IS 'Company NPWP used for auto-splitting Faktur Pajak into Point A and B';
COMMENT ON COLUMN ppn_projects.point_a_count IS 'Count of Faktur Pajak Keluaran (Output Tax)';
COMMENT ON COLUMN ppn_projects.point_b_count IS 'Count of Faktur Pajak Masukan (Input Tax)';
COMMENT ON COLUMN ppn_projects.point_c_count IS 'Count of Bukti Potong Lawan Transaksi';
COMMENT ON COLUMN ppn_projects.point_e_count IS 'Count of Rekening Koran transactions';

-- ==================== PPN Data Sources Table ====================

CREATE TABLE IF NOT EXISTS ppn_data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES ppn_projects(id) ON DELETE CASCADE,

    -- Source identification
    point_type VARCHAR(20) NOT NULL CHECK (point_type IN ('point_a_b', 'point_c', 'point_e')),
    source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('scanned', 'upload')),

    -- File reference
    excel_export_id UUID REFERENCES excel_exports(id) ON DELETE SET NULL,
    uploaded_file_path VARCHAR(500),

    -- File metadata
    filename VARCHAR(255) NOT NULL,
    row_count INTEGER DEFAULT 0,

    -- Processing status
    processing_status VARCHAR(50) DEFAULT 'pending'
        CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,

    -- Audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,

    -- Constraints
    CONSTRAINT ppn_data_sources_pkey PRIMARY KEY (id),
    CONSTRAINT valid_source_reference CHECK (
        (source_type = 'scanned' AND excel_export_id IS NOT NULL) OR
        (source_type = 'upload' AND uploaded_file_path IS NOT NULL)
    )
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_ppn_data_sources_project_id ON ppn_data_sources(project_id);
CREATE INDEX IF NOT EXISTS idx_ppn_data_sources_point_type ON ppn_data_sources(point_type);
CREATE INDEX IF NOT EXISTS idx_ppn_data_sources_excel_export_id ON ppn_data_sources(excel_export_id);
CREATE INDEX IF NOT EXISTS idx_ppn_data_sources_status ON ppn_data_sources(processing_status);

-- Add comments
COMMENT ON TABLE ppn_data_sources IS 'Data sources for PPN reconciliation (scanned or uploaded files)';
COMMENT ON COLUMN ppn_data_sources.point_type IS 'Type of data point: point_a_b (Faktur Pajak), point_c (Bukti Potong), point_e (Rekening Koran)';
COMMENT ON COLUMN ppn_data_sources.source_type IS 'Source type: scanned (from OCR) or upload (manual upload)';

-- ==================== PPN Point A Data Table ====================

CREATE TABLE IF NOT EXISTS ppn_point_a (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES ppn_projects(id) ON DELETE CASCADE,
    data_source_id UUID NOT NULL REFERENCES ppn_data_sources(id) ON DELETE CASCADE,

    -- Faktur Pajak Keluaran data (when company is seller)
    nomor_faktur VARCHAR(100),
    tanggal_faktur DATE,
    npwp_seller VARCHAR(20),  -- Should match company_npwp
    nama_seller VARCHAR(200),
    npwp_buyer VARCHAR(20),
    nama_buyer VARCHAR(200),

    -- Amount fields
    dpp NUMERIC(15, 2),
    ppn NUMERIC(15, 2),
    total NUMERIC(15, 2),

    -- Reconciliation status
    is_matched BOOLEAN DEFAULT FALSE,
    matched_with_point_c_id UUID,  -- References ppn_point_c.id
    match_confidence NUMERIC(5, 2),
    match_type VARCHAR(50),

    -- Metadata
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT ppn_point_a_pkey PRIMARY KEY (id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_ppn_point_a_project_id ON ppn_point_a(project_id);
CREATE INDEX IF NOT EXISTS idx_ppn_point_a_data_source_id ON ppn_point_a(data_source_id);
CREATE INDEX IF NOT EXISTS idx_ppn_point_a_nomor_faktur ON ppn_point_a(nomor_faktur);
CREATE INDEX IF NOT EXISTS idx_ppn_point_a_tanggal_faktur ON ppn_point_a(tanggal_faktur);
CREATE INDEX IF NOT EXISTS idx_ppn_point_a_is_matched ON ppn_point_a(is_matched);
CREATE INDEX IF NOT EXISTS idx_ppn_point_a_npwp_buyer ON ppn_point_a(npwp_buyer);

-- Add comments
COMMENT ON TABLE ppn_point_a IS 'Point A: Faktur Pajak Keluaran (Output Tax) - Company is the seller';

-- ==================== PPN Point B Data Table ====================

CREATE TABLE IF NOT EXISTS ppn_point_b (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES ppn_projects(id) ON DELETE CASCADE,
    data_source_id UUID NOT NULL REFERENCES ppn_data_sources(id) ON DELETE CASCADE,

    -- Faktur Pajak Masukan data (when company is buyer)
    nomor_faktur VARCHAR(100),
    tanggal_faktur DATE,
    npwp_seller VARCHAR(20),
    nama_seller VARCHAR(200),
    npwp_buyer VARCHAR(20),  -- Should match company_npwp
    nama_buyer VARCHAR(200),

    -- Amount fields
    dpp NUMERIC(15, 2),
    ppn NUMERIC(15, 2),
    total NUMERIC(15, 2),

    -- Reconciliation status
    is_matched BOOLEAN DEFAULT FALSE,
    matched_with_point_e_id UUID,  -- References ppn_point_e.id
    match_confidence NUMERIC(5, 2),
    match_type VARCHAR(50),

    -- Metadata
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT ppn_point_b_pkey PRIMARY KEY (id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_ppn_point_b_project_id ON ppn_point_b(project_id);
CREATE INDEX IF NOT EXISTS idx_ppn_point_b_data_source_id ON ppn_point_b(data_source_id);
CREATE INDEX IF NOT EXISTS idx_ppn_point_b_nomor_faktur ON ppn_point_b(nomor_faktur);
CREATE INDEX IF NOT EXISTS idx_ppn_point_b_tanggal_faktur ON ppn_point_b(tanggal_faktur);
CREATE INDEX IF NOT EXISTS idx_ppn_point_b_is_matched ON ppn_point_b(is_matched);
CREATE INDEX IF NOT EXISTS idx_ppn_point_b_npwp_seller ON ppn_point_b(npwp_seller);

-- Add comments
COMMENT ON TABLE ppn_point_b IS 'Point B: Faktur Pajak Masukan (Input Tax) - Company is the buyer';

-- ==================== PPN Point C Data Table ====================

CREATE TABLE IF NOT EXISTS ppn_point_c (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES ppn_projects(id) ON DELETE CASCADE,
    data_source_id UUID NOT NULL REFERENCES ppn_data_sources(id) ON DELETE CASCADE,

    -- Bukti Potong data
    nomor_bukti_potong VARCHAR(100),
    tanggal_bukti_potong DATE,
    npwp_pemotong VARCHAR(20),  -- Who withheld the tax
    nama_pemotong VARCHAR(200),
    npwp_dipotong VARCHAR(20),   -- Who got the tax withheld (should match company_npwp for Point A reconciliation)
    nama_dipotong VARCHAR(200),

    -- Amount fields
    jumlah_penghasilan_bruto NUMERIC(15, 2),
    tarif_pph NUMERIC(5, 2),  -- Tax rate (%)
    pph_dipotong NUMERIC(15, 2),  -- Tax amount withheld

    -- Reconciliation status
    is_matched BOOLEAN DEFAULT FALSE,
    matched_with_point_a_id UUID,  -- References ppn_point_a.id
    match_confidence NUMERIC(5, 2),
    match_type VARCHAR(50),

    -- Metadata
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT ppn_point_c_pkey PRIMARY KEY (id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_ppn_point_c_project_id ON ppn_point_c(project_id);
CREATE INDEX IF NOT EXISTS idx_ppn_point_c_data_source_id ON ppn_point_c(data_source_id);
CREATE INDEX IF NOT EXISTS idx_ppn_point_c_nomor_bukti_potong ON ppn_point_c(nomor_bukti_potong);
CREATE INDEX IF NOT EXISTS idx_ppn_point_c_tanggal ON ppn_point_c(tanggal_bukti_potong);
CREATE INDEX IF NOT EXISTS idx_ppn_point_c_is_matched ON ppn_point_c(is_matched);
CREATE INDEX IF NOT EXISTS idx_ppn_point_c_npwp_dipotong ON ppn_point_c(npwp_dipotong);

-- Add comments
COMMENT ON TABLE ppn_point_c IS 'Point C: Bukti Potong Lawan Transaksi (Withholding Tax Certificates)';

-- ==================== PPN Point E Data Table ====================

CREATE TABLE IF NOT EXISTS ppn_point_e (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES ppn_projects(id) ON DELETE CASCADE,
    data_source_id UUID NOT NULL REFERENCES ppn_data_sources(id) ON DELETE CASCADE,

    -- Rekening Koran data
    tanggal_transaksi DATE,
    keterangan TEXT,
    nominal NUMERIC(15, 2),
    jenis_transaksi VARCHAR(20) CHECK (jenis_transaksi IN ('debit', 'credit')),

    -- Bank details
    bank_name VARCHAR(100),
    account_number VARCHAR(100),

    -- Reconciliation status
    is_matched BOOLEAN DEFAULT FALSE,
    matched_with_point_b_id UUID,  -- References ppn_point_b.id
    match_confidence NUMERIC(5, 2),
    match_type VARCHAR(50),

    -- Metadata
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT ppn_point_e_pkey PRIMARY KEY (id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_ppn_point_e_project_id ON ppn_point_e(project_id);
CREATE INDEX IF NOT EXISTS idx_ppn_point_e_data_source_id ON ppn_point_e(data_source_id);
CREATE INDEX IF NOT EXISTS idx_ppn_point_e_tanggal ON ppn_point_e(tanggal_transaksi);
CREATE INDEX IF NOT EXISTS idx_ppn_point_e_is_matched ON ppn_point_e(is_matched);
CREATE INDEX IF NOT EXISTS idx_ppn_point_e_nominal ON ppn_point_e(nominal);

-- Add comments
COMMENT ON TABLE ppn_point_e IS 'Point E: Rekening Koran (Bank Statement) transactions';

-- ==================== Triggers ====================

-- Auto-update updated_at for ppn_projects
CREATE OR REPLACE FUNCTION update_ppn_projects_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ppn_projects_updated_at_trigger
    BEFORE UPDATE ON ppn_projects
    FOR EACH ROW
    EXECUTE FUNCTION update_ppn_projects_updated_at();

-- Auto-update point counts when data is inserted/deleted
CREATE OR REPLACE FUNCTION update_ppn_project_counts()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT' OR TG_OP = 'UPDATE') THEN
        -- Update counts based on table
        IF TG_TABLE_NAME = 'ppn_point_a' THEN
            UPDATE ppn_projects SET point_a_count = (
                SELECT COUNT(*) FROM ppn_point_a WHERE project_id = NEW.project_id
            ) WHERE id = NEW.project_id;
        ELSIF TG_TABLE_NAME = 'ppn_point_b' THEN
            UPDATE ppn_projects SET point_b_count = (
                SELECT COUNT(*) FROM ppn_point_b WHERE project_id = NEW.project_id
            ) WHERE id = NEW.project_id;
        ELSIF TG_TABLE_NAME = 'ppn_point_c' THEN
            UPDATE ppn_projects SET point_c_count = (
                SELECT COUNT(*) FROM ppn_point_c WHERE project_id = NEW.project_id
            ) WHERE id = NEW.project_id;
        ELSIF TG_TABLE_NAME = 'ppn_point_e' THEN
            UPDATE ppn_projects SET point_e_count = (
                SELECT COUNT(*) FROM ppn_point_e WHERE project_id = NEW.project_id
            ) WHERE id = NEW.project_id;
        END IF;
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        -- Update counts based on table
        IF TG_TABLE_NAME = 'ppn_point_a' THEN
            UPDATE ppn_projects SET point_a_count = (
                SELECT COUNT(*) FROM ppn_point_a WHERE project_id = OLD.project_id
            ) WHERE id = OLD.project_id;
        ELSIF TG_TABLE_NAME = 'ppn_point_b' THEN
            UPDATE ppn_projects SET point_b_count = (
                SELECT COUNT(*) FROM ppn_point_b WHERE project_id = OLD.project_id
            ) WHERE id = OLD.project_id;
        ELSIF TG_TABLE_NAME = 'ppn_point_c' THEN
            UPDATE ppn_projects SET point_c_count = (
                SELECT COUNT(*) FROM ppn_point_c WHERE project_id = OLD.project_id
            ) WHERE id = OLD.project_id;
        ELSIF TG_TABLE_NAME = 'ppn_point_e' THEN
            UPDATE ppn_projects SET point_e_count = (
                SELECT COUNT(*) FROM ppn_point_e WHERE project_id = OLD.project_id
            ) WHERE id = OLD.project_id;
        END IF;
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for auto-updating counts
CREATE TRIGGER ppn_point_a_count_trigger
    AFTER INSERT OR DELETE ON ppn_point_a
    FOR EACH ROW
    EXECUTE FUNCTION update_ppn_project_counts();

CREATE TRIGGER ppn_point_b_count_trigger
    AFTER INSERT OR DELETE ON ppn_point_b
    FOR EACH ROW
    EXECUTE FUNCTION update_ppn_project_counts();

CREATE TRIGGER ppn_point_c_count_trigger
    AFTER INSERT OR DELETE ON ppn_point_c
    FOR EACH ROW
    EXECUTE FUNCTION update_ppn_project_counts();

CREATE TRIGGER ppn_point_e_count_trigger
    AFTER INSERT OR DELETE ON ppn_point_e
    FOR EACH ROW
    EXECUTE FUNCTION update_ppn_project_counts();
