-- 券商 / 分行參考表（實際部署版本）

-- Table: public.brokers
-- DROP TABLE IF EXISTS public.brokers;

CREATE TABLE IF NOT EXISTS public.brokers
(
    broker_code character varying(50) COLLATE pg_catalog."default" NOT NULL,
    broker_name character varying(200) COLLATE pg_catalog."default",
    fetched_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT brokers_pkey PRIMARY KEY (broker_code)
)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.brokers
    OWNER to postgres;

-- Index: idx_brokers_name
CREATE INDEX IF NOT EXISTS idx_brokers_name
    ON public.brokers USING btree
    (broker_name COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;


-- Table: public.branches
-- DROP TABLE IF EXISTS public.branches;

CREATE TABLE IF NOT EXISTS public.branches
(
    broker_code character varying(50) COLLATE pg_catalog."default" NOT NULL,
    branch_code_raw text COLLATE pg_catalog."default" NOT NULL,
    branch_code character varying(50) COLLATE pg_catalog."default",
    branch_name character varying(200) COLLATE pg_catalog."default",
    is_broker_level boolean DEFAULT false,
    fetched_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT branches_pkey PRIMARY KEY (broker_code, branch_code_raw),
    CONSTRAINT branches_fk_broker FOREIGN KEY (broker_code)
        REFERENCES public.brokers (broker_code) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.branches
    OWNER to postgres;

-- Index: idx_branches_branch_code
CREATE INDEX IF NOT EXISTS idx_branches_branch_code
    ON public.branches USING btree
    (branch_code COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;

-- Index: idx_branches_name
CREATE INDEX IF NOT EXISTS idx_branches_name
    ON public.branches USING btree
    (branch_name COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
