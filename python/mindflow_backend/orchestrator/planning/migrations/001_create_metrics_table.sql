-- Migration: Create planning_trigger_metrics table
-- Date: 2026-03-18

CREATE TABLE IF NOT EXISTS planning_trigger_metrics (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    plan_id VARCHAR(64),
    trigger_decision BOOLEAN NOT NULL,
    confidence FLOAT NOT NULL,
    user_confirmed BOOLEAN,
    execution_completed BOOLEAN,
    latency_ms FLOAT NOT NULL,
    method_used VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_planning_metrics_session ON planning_trigger_metrics(session_id);
CREATE INDEX IF NOT EXISTS idx_planning_metrics_plan ON planning_trigger_metrics(plan_id);
CREATE INDEX IF NOT EXISTS idx_planning_metrics_method ON planning_trigger_metrics(method_used);
CREATE INDEX IF NOT EXISTS idx_planning_metrics_timestamp ON planning_trigger_metrics(timestamp);

-- Comments
COMMENT ON TABLE planning_trigger_metrics IS 'Metrics for planning trigger decisions and outcomes';
COMMENT ON COLUMN planning_trigger_metrics.trigger_decision IS 'Whether planning was triggered';
COMMENT ON COLUMN planning_trigger_metrics.confidence IS 'Confidence score [0, 1]';
COMMENT ON COLUMN planning_trigger_metrics.latency_ms IS 'Decision latency in milliseconds';
COMMENT ON COLUMN planning_trigger_metrics.method_used IS 'Method: llm, fallback, or legacy';
