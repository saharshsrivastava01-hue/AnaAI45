-- Supports bounded scheduled deletion of expired per-IP rate-limit buckets.
CREATE INDEX IF NOT EXISTS idx_rate_limits_window_started
  ON rate_limits(window_started);
