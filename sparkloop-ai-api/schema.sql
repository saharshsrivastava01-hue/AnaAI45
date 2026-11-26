-- Optional persistent database schema for SparkLoop AI.
-- Apply only to a database dedicated to this app. Never reuse another app's tables.
CREATE SCHEMA IF NOT EXISTS sparkloop;
CREATE TABLE IF NOT EXISTS sparkloop.users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS sparkloop.workspaces (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id UUID NOT NULL REFERENCES sparkloop.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS sparkloop.content_drafts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES sparkloop.workspaces(id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','scheduled','published','archived')),
  scheduled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS sparkloop.campaigns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES sparkloop.workspaces(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  objective TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','active','paused','completed')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS sparkloop.wallet_ledger (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES sparkloop.users(id) ON DELETE CASCADE,
  direction TEXT NOT NULL CHECK (direction IN ('credit','debit')),
  amount_paise BIGINT NOT NULL CHECK (amount_paise > 0),
  currency CHAR(3) NOT NULL DEFAULT 'INR',
  provider TEXT NOT NULL,
  provider_reference TEXT NOT NULL UNIQUE,
  verification_status TEXT NOT NULL CHECK (verification_status IN ('pending','verified','failed','reversed')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- Wallet balance is always calculated from verified ledger entries.
CREATE OR REPLACE VIEW sparkloop.wallet_balances AS
SELECT user_id,
  COALESCE(SUM(CASE WHEN verification_status='verified' AND direction='credit' THEN amount_paise
                    WHEN verification_status='verified' AND direction='debit' THEN -amount_paise
                    ELSE 0 END),0)::BIGINT AS balance_paise
FROM sparkloop.wallet_ledger
GROUP BY user_id;
