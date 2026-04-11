-- DDL: brokers and branches reference tables
-- Brokers (issuer) table
CREATE TABLE IF NOT EXISTS public.brokers (
    broker_code character varying(50) NOT NULL,
    broker_name character varying(200),
    fetched_at timestamptz,
    created_at timestamptz DEFAULT now(),
    CONSTRAINT brokers_pkey PRIMARY KEY (broker_code)
);

ALTER TABLE IF EXISTS public.brokers
    OWNER TO postgres;

-- Branches table: composite PK (broker_code, branch_code_raw) because branch codes are unique per broker
CREATE TABLE IF NOT EXISTS public.branches (
    broker_code character varying(50) NOT NULL,
    branch_code_raw text NOT NULL,
    branch_code character varying(50),
    branch_name character varying(200),
    is_broker_level boolean DEFAULT FALSE,
    fetched_at timestamptz,
    created_at timestamptz DEFAULT now(),
    CONSTRAINT branches_pkey PRIMARY KEY (broker_code, branch_code_raw),
    CONSTRAINT branches_fk_broker FOREIGN KEY (broker_code) REFERENCES public.brokers(broker_code)
);

ALTER TABLE IF EXISTS public.branches
    OWNER TO postgres;

CREATE INDEX IF NOT EXISTS idx_branches_branch_code ON public.branches (branch_code);
CREATE INDEX IF NOT EXISTS idx_brokers_name ON public.brokers (broker_name);
CREATE INDEX IF NOT EXISTS idx_branches_name ON public.branches (branch_name);
