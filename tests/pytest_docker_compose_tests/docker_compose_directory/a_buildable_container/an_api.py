import uvicorn
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI

app = FastAPI()
CONNECTION = psycopg2.connect(dbname='postgres', user='postgres', host='my_db', port=5432)


def cursor_do(sql, data=()):
    try:
        cursor = CONNECTION.cursor(cursor_factory=RealDictCursor)
        cursor.execute(sql, data)
        try:
            result = [row for row in cursor.fetchall()]
        except psycopg2.ProgrammingError:
            result = None
        CONNECTION.commit()
    finally:
        cursor.close()
    return result[0] if result and len(result) == 1 else result


def create_database():
    cursor_do("CREATE TABLE my_table (id serial PRIMARY KEY, num integer, data varchar);")


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/all")
def read_all():
    return cursor_do("SELECT * FROM my_table;")


@app.get("/items/{item_id}")
def read_item(item_id: int):
    return cursor_do("SELECT * FROM my_table WHERE num=%s;", (item_id, ))


@app.put("/items/{item_id}")
def put_item(item_id: int, data_string: str = "abc'def"):
    return cursor_do("INSERT INTO my_table (num, data) VALUES (%s, %s)", (item_id, data_string))


if __name__ == "__main__":
    try:
        create_database()
        uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
    finally:
        CONNECTION.close()
