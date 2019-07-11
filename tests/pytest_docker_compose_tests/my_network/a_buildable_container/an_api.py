import uvicorn
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI

app = FastAPI()


def create_database():
    with CONNECTION.cursor() as cursor:
        cursor.execute("CREATE TABLE my_table (id serial PRIMARY KEY, num integer, data varchar);")
        CONNECTION.commit()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/all")
def read_all():
    with CONNECTION.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute('SELECT * FROM my_table;')
        return [row for row in cursor.fetchall()]


@app.get("/items/{item_id}")
def read_item(item_id: int):
    with CONNECTION.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute('SELECT * FROM my_table WHERE num=%s;', (item_id, ))
        return cursor.fetchone()


@app.put("/items/{item_id}")
def put_item(item_id: int, data_string: str = "abc'def"):
    with CONNECTION.cursor() as cursor:
        cursor.execute("INSERT INTO my_table (num, data) VALUES (%s, %s) "
                       "RETURNING *;", (item_id, data_string))
        CONNECTION.commit()
        return cursor.fetchone()


@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    with CONNECTION.cursor() as cursor:
        cursor.execute('DELETE FROM my_table WHERE num=%s RETURNING *;', (item_id, ))
        CONNECTION.commit()
        return cursor.fetchone()


if __name__ == "__main__":
    try:
        CONNECTION = psycopg2.connect(dbname='postgres', user='postgres', host='my_db', port=5432)
        create_database()
        uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
    finally:
        CONNECTION.close()
