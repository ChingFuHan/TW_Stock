-- DDL for stock_flow_lots_detailed
CREATE TABLE IF NOT EXISTS public.stock_flow_lots_detailed (
    da timestamp without time zone NOT NULL,
    stock_code character varying(50) COLLATE pg_catalog."default" NOT NULL,
    stock_name character varying(100) COLLATE pg_catalog."default" NOT NULL,
    broker_code character varying(50) COLLATE pg_catalog."default",
    branch_code character varying(50) COLLATE pg_catalog."default",
    branch_code_raw text,
    broker_name text,
    branch_name text,
    buy_lots bigint,
    sell_lots bigint,
    net_lots bigint,
    source_url text,
    fetched_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT stock_flow_lots_detailed_pkey PRIMARY KEY (da, stock_code, broker_code, branch_code)
)
TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS stock_flow_stock_date_idx ON public.stock_flow_lots_detailed (stock_code, da DESC);
CREATE INDEX IF NOT EXISTS stock_flow_da_idx ON public.stock_flow_lots_detailed (da);
CREATE INDEX IF NOT EXISTS stock_flow_broker_branch_da_idx ON public.stock_flow_lots_detailed (broker_code, branch_code, da);
