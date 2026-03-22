import sqlite3

con = sqlite3.connect(r'd:\astroq-mar26\backend\astroq.db')
tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

for t in tables:
    name = t[0]
    count = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
    print(f"Table: {name}, Rows: {count}")
