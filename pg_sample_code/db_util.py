# -*- coding: UTF-8 -*-
# !/usr/bin/python
# 2020-09-01 fix pool
# 2020-09-03 adding 98 fetchall
# 2020-12-22 inactive module mosql
import os
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
# import mosql

# 載入 .env（若有），機密一律從環境變數讀取，不再寫死於原始碼
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

eikon_token = os.environ.get("EIKON_TOKEN", "")

pg_host = os.environ.get("PGHOST", "127.0.0.1")
pg_port = os.environ.get("PGPORT", "5432")
pg_user = os.environ.get("PGUSER", "postgres")
pg_passwd = os.environ.get("PGPASSWORD", "")

pg_host98 = os.environ.get("PGHOST98", "127.0.0.1")
pg_port98 = os.environ.get("PGPORT98", "5432")
pg_user98 = os.environ.get("PGUSER98", "postgres")
pg_passwd98 = os.environ.get("PGPASSWORD98", "")


conn_pools = {}
conn_pools98 = {}
conn_pools59 = {}

def getconn(database):
    if database not in conn_pools:
        dsn = "host='%s' port='%s' dbname='%s' user='%s' password='%s' " % (
            pg_host, pg_port, database, pg_user, pg_passwd)
        conn_pools[database] = ThreadedConnectionPool(1, 5, dsn=dsn)
    return conn_pools[database].getconn()

def getconn98(database):
    if database not in conn_pools98:
        dsn = "host='%s' port='%s' dbname='%s' user='%s' password='%s'" % (
            pg_host98, pg_port98, database, pg_user98, pg_passwd98)
        conn_pools98[database] = ThreadedConnectionPool(1, 5, dsn=dsn)
    return conn_pools98[database].getconn()

def getconn59(database):
    host59 = os.environ.get("PGHOST59", "127.0.0.1")
    port59 = os.environ.get("PGPORT59", "5432")
    user59 = os.environ.get("PGUSER59", "postgres")
    passwd59 = os.environ.get("PGPASSWORD59", "")
    if database not in conn_pools59:
        dsn = "host='%s' port='%s' dbname='%s' user='%s' password='%s'" % (
            host59, port59, database, user59, passwd59)
        conn_pools59[database] = ThreadedConnectionPool(1, 5, dsn=dsn)
    return conn_pools59[database].getconn()

def db99Query(database, sqlstring):
    conn = getconn(database)
    cur = conn.cursor()
    try:
        cur.execute(sqlstring)
        r = cur.fetchall()
        cur.close()
    except (Exception, psycopg2.Error) as error:
        r = None
    finally:
        conn_pools[database].putconn(conn)
        return r


def db99fetchall(database, sqlstring):
    conn = getconn(database)
    cur = conn.cursor()
    try:
        cur.execute(sqlstring)
        r = cur.fetchall()
        cur.close()
    except (Exception, psycopg2.Error) as error:
        r = None
    finally:
        conn_pools[database].putconn(conn)
        return r

def db99fetchall_dict(database, sqlstring):
    conn = getconn(database)
    cur = conn.cursor()
    try:
        cur.execute(sqlstring)
        names = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        out = []
        for row in rows:
            out.append(dict(zip(names, row)))
        cur.close()
    except (Exception, psycopg2.Error) as error:
        out = []
    finally:
        conn_pools[database].putconn(conn)
        return out


def db98fetchall(database, sqlstring):
    conn = getconn98(database)
    cur = conn.cursor()
    try:
        cur.execute(sqlstring)
        r = cur.fetchall()
        cur.close()
    except (Exception, psycopg2.Error) as error:
        r = None
    finally:
        conn_pools98[database].putconn(conn)
        return r
def db98fetchall_dict(database, sqlstring):
    conn = getconn98(database)
    cur = conn.cursor()
    try:
        cur.execute(sqlstring)
        names = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        out = []
        for row in rows:
            out.append(dict(zip(names, row)))
        cur.close()
    except (Exception, psycopg2.Error) as error:
        out = []
    finally:
        conn_pools98[database].putconn(conn)
        return out
def db59fetchall(database, sqlstring):
    conn = getconn59(database)
    cur = conn.cursor()
    try:
        cur.execute(sqlstring)
        r = cur.fetchall()
        cur.close()
    except (Exception, psycopg2.Error) as error:
        r = None
    finally:
        conn_pools59[database].putconn(conn)
        return r

def db59fetchall_dict(database, sqlstring):
    conn = getconn59(database)
    cur = conn.cursor()
    try:
        cur.execute(sqlstring)
        names = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        out = []
        for row in rows:
            out.append(dict(zip(names, row)))
        cur.close()
    except (Exception, psycopg2.Error) as error:
        out = []
    finally:
        conn_pools59[database].putconn(conn)
        return out

def db99fetchone(database, sqlstring):
    conn = getconn(database)
    cur = conn.cursor()
    try:
        cur.execute(sqlstring)
        r = cur.fetchone()
        cur.close()
    except (Exception, psycopg2.Error) as error:
        r = None
    finally:
        conn_pools[database].putconn(conn)
        return r


def db99exec(database, sqlstring):
    conn = getconn(database)
    cur = conn.cursor()
    try:
        cur.execute(sqlstring)
        conn.commit()
        cur.close()
    except (Exception, psycopg2.Error) as error:
        conn.rollback()
        cur.close()
        return error
    finally:
        cur.close()
        conn_pools[database].putconn(conn)

def db98exec(database, sqlstring):
    conn = getconn98(database)
    cur = conn.cursor()
    try:
        cur.execute(sqlstring)
        conn.commit()
        cur.close()
    except (Exception, psycopg2.Error) as error:
        conn.rollback()
    finally:
        conn_pools98[database].putconn(conn)


def db59exec(database, sqlstring):
    conn = getconn59(database)
    cur = conn.cursor()
    try:
        cur.execute(sqlstring)
        conn.commit()
        cur.close()
    except (Exception, psycopg2.Error) as error:
        conn.rollback()
    finally:
        conn_pools59[database].putconn(conn)

if __name__ == "__main__":
    sql  ="select * from price limit 1"
    db99exec('tw', sql)
    a=1
