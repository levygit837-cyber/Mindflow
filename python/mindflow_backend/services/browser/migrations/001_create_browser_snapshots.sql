-- Migration: Create browser_snapshots table
-- Description: Store LightPanda browser snapshots in PostgreSQL
-- Created: 2026-04-06

CREATE TABLE IF NOT EXISTS browser_snapshots (
    id BIGSERIAL PRIMARY KEY,
    snapshot_id VARCHAR(255) NOT NULL UNIQUE,
    browser_id VARCHAR(255) NOT NULL,
    url TEXT,
    cookies JSONB,
    local_storage JSONB,
    session_storage JSONB,
    page_state JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Indexes for common queries
    INDEX idx_browser_snapshots_browser_id (browser_id),
    INDEX idx_browser_snapshots_snapshot_id (snapshot_id),
    INDEX idx_browser_snapshots_created_at (created_at),
    INDEX idx_browser_snapshots_expires_at (expires_at),
    INDEX idx_browser_snapshots_is_active (is_active)
);

-- Add comment
COMMENT ON TABLE browser_snapshots IS 'Stores LightPanda browser state snapshots for rollback capabilities';
COMMENT ON COLUMN browser_snapshots.snapshot_id IS 'Unique identifier for the snapshot';
COMMENT ON COLUMN browser_snapshots.browser_id IS 'ID of the browser instance';
COMMENT ON COLUMN browser_snapshots.expires_at IS 'When the snapshot should be automatically cleaned up';
COMMENT ON COLUMN browser_snapshots.is_active IS 'Whether the snapshot is still valid';
COMMENT ON COLUMN browser_snapshots.metadata IS 'Additional metadata about the snapshot';

-- Create function to clean up expired snapshots
CREATE OR REPLACE FUNCTION cleanup_expired_snapshots()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM browser_snapshots
    WHERE expires_at IS NOT NULL
      AND expires_at < NOW()
      AND is_active = TRUE;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_expired_snapshots IS 'Cleans up expired snapshots and returns the count of deleted records';
