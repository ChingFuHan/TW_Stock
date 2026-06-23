-- Table: public.stock_flow_lots_detailed
-- 實際部署版本（欄名為 legacy 的 code / cname）。回補主表，由 db_writer.py 寫入。

-- DROP TABLE IF EXISTS public.stock_flow_lots_detailed;

CREATE TABLE IF NOT EXISTS public.stock_flow_lots_detailed
(
    da timestamp without time zone NOT NULL,
    code character varying(50) COLLATE pg_catalog."default" NOT NULL,
    cname character varying(50) COLLATE pg_catalog."default" NOT NULL,
    broker_code character varying(50) COLLATE pg_catalog."default" NOT NULL,
    branch_code character varying(50) COLLATE pg_catalog."default" NOT NULL,
    branch_code_raw text COLLATE pg_catalog."default",
    broker_name text COLLATE pg_catalog."default",
    branch_name text COLLATE pg_catalog."default",
    buy_lots bigint,
    sell_lots bigint,
    net_lots bigint,
    source_url text COLLATE pg_catalog."default",
    fetched_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT stock_flow_lots_detailed_pkey PRIMARY KEY (da, code, broker_code, branch_code)
)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.stock_flow_lots_detailed
    OWNER to postgres;

-- Index: idx_stock_flow_broker_branch_da
CREATE INDEX IF NOT EXISTS idx_stock_flow_broker_branch_da
    ON public.stock_flow_lots_detailed USING btree
    (broker_code COLLATE pg_catalog."default" ASC NULLS LAST, branch_code COLLATE pg_catalog."default" ASC NULLS LAST, da ASC NULLS LAST)
    TABLESPACE pg_default;

-- Index: idx_stock_flow_code_da
CREATE INDEX IF NOT EXISTS idx_stock_flow_code_da
    ON public.stock_flow_lots_detailed USING btree
    (code COLLATE pg_catalog."default" ASC NULLS LAST, da DESC NULLS FIRST)
    TABLESPACE pg_default;

-- Index: idx_stock_flow_da
CREATE INDEX IF NOT EXISTS idx_stock_flow_da
    ON public.stock_flow_lots_detailed USING btree
    (da ASC NULLS LAST)
    TABLESPACE pg_default;

-- 註：以下兩個索引與上面的 idx_stock_flow_broker_branch_da / idx_stock_flow_da 定義相同，
--     為生產環境累積的重複索引；全新建置可擇一保留（保留於此以忠實反映部署狀態）。

-- Index: stock_flow_broker_branch_da_idx
CREATE INDEX IF NOT EXISTS stock_flow_broker_branch_da_idx
    ON public.stock_flow_lots_detailed USING btree
    (broker_code COLLATE pg_catalog."default" ASC NULLS LAST, branch_code COLLATE pg_catalog."default" ASC NULLS LAST, da ASC NULLS LAST)
    TABLESPACE pg_default;

-- Index: stock_flow_da_idx
CREATE INDEX IF NOT EXISTS stock_flow_da_idx
    ON public.stock_flow_lots_detailed USING btree
    (da ASC NULLS LAST)
    TABLESPACE pg_default;
