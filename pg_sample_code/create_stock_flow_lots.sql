-- DDL for stock_flow_lots
CREATE TABLE IF NOT EXISTS public.stock_flow_lots (
    trade_date date NOT NULL,
    metric_type varchar(16) NOT NULL DEFAULT 'lots',
    broker_code varchar(32) NOT NULL,
    branch_code varchar(32) NOT NULL,
    branch_code_raw text,
    broker_name text,
    branch_name text,
    stock_code varchar(32) NOT NULL,
    stock_name text,
    buy_lots bigint,
    sell_lots bigint,
    net_lots bigint,
    source_url text,
    fetched_at timestamptz,
    created_at timestamptz DEFAULT now(),
    CONSTRAINT stock_flow_lots_pkey PRIMARY KEY (trade_date, broker_code, branch_code, stock_code, metric_type)
);

CREATE INDEX IF NOT EXISTS stock_flow_stock_date_idx ON public.stock_flow_lots (stock_code, trade_date DESC);
CREATE INDEX IF NOT EXISTS stock_flow_trade_date_idx ON public.stock_flow_lots (trade_date);
CREATE INDEX IF NOT EXISTS stock_flow_broker_branch_date_idx ON public.stock_flow_lots (broker_code, branch_code, trade_date);
