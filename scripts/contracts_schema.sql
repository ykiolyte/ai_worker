CREATE TABLE IF NOT EXISTS contract_drafts (
    id UUID PRIMARY KEY,
    product_id UUID NOT NULL,
    supplier_contact_id UUID NOT NULL,
    agent_task_id UUID,
    supplier_name TEXT NOT NULL,
    status TEXT NOT NULL,
    title TEXT NOT NULL,
    extracted_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    draft_text TEXT,
    file_name TEXT NOT NULL,
    content_type TEXT NOT NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_contract_drafts_product_id ON contract_drafts(product_id);
CREATE INDEX IF NOT EXISTS idx_contract_drafts_supplier_contact_id ON contract_drafts(supplier_contact_id);
CREATE INDEX IF NOT EXISTS idx_contract_drafts_status ON contract_drafts(status);
