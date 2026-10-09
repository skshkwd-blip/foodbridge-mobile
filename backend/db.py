"""Small drop-in replacement for flask_mysqldb's MySQL object, built on PyMySQL.

PyMySQL is pure Python, so it installs on free hosts with no build tools.
Interface used by the app: mysql.connection.cursor() / .commit() / .rollback().
Supports SSL (MYSQL_USE_SSL=true), which hosted databases such as Aiven require.

Two safety features for long-running servers:
  * the connection is checked before each use and re-opened if the server dropped it
  * every request ends by closing any open transaction, so the next request on the
    same worker always sees fresh data instead of an old snapshot
"""
import ssl as ssl_lib

import pymysql
import pymysql.cursors


class MySQL:
    def __init__(self, app=None):
        self.app = None
        self._connection = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        app.teardown_request(self._end_transaction)

    def _end_transaction(self, exc=None):
        conn = self._connection
        if conn is not None and conn.open:
            try:
                conn.rollback()      # routes that write always commit() first
            except Exception:
                pass

    @property
    def connection(self):
        conn = self._connection
        if conn is not None and conn.open:
            try:
                conn.ping(reconnect=False)
                return conn
            except Exception:
                pass                 # dropped by the server: open a new one below

        cfg = self.app.config
        ssl_ctx = None
        if cfg.get('MYSQL_USE_SSL'):
            ssl_ctx = ssl_lib.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl_lib.CERT_NONE
        self._connection = pymysql.connect(
            host=cfg['MYSQL_HOST'],
            user=cfg['MYSQL_USER'],
            password=cfg['MYSQL_PASSWORD'],
            db=cfg['MYSQL_DB'],
            port=cfg.get('MYSQL_PORT', 3306),
            cursorclass=pymysql.cursors.Cursor,
            autocommit=False,
            ssl=ssl_ctx,
        )
        return self._connection


# Single shared instance: app.py and models.py import this same object
mysql = MySQL()
