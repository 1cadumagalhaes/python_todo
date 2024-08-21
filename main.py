from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import json
import pymongo

from pymongo.errors import BulkWriteError
from contextlib import asynccontextmanager

client, db, todos_collection = None, None, None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client, db, todos_collection
    client = pymongo.MongoClient("localhost", 27017)
    db = client.todo_database
    todos_collection = db.todos
    todos_collection.create_index([("id", pymongo.ASCENDING)], unique=True)
    yield
    client.close()


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def root(request: Request):
    data = list(todos_collection.find({}, {"_id": 0}))
    tododict = {str(todo["id"]): todo["description"] for todo in data}
    return templates.TemplateResponse(
        "todolist.html", {"request": request, "tododict": tododict}
    )


@app.get("/delete/{id}")
async def delete_todo(request: Request, id: str):
    with open("database.json") as f:
        data = json.load(f)
    del data[id]
    with open("database.json", "w") as f:
        json.dump(data, f)
    return RedirectResponse("/", 303)


@app.post("/add")
async def add_todo(request: Request):
    with open("database.json") as f:
        data = json.load(f)
    formdata = await request.form()
    newdata = {}
    i = 1
    for id in data:
        newdata[str(i)] = data[id]
        i += 1
    newdata[str(i)] = formdata["newtodo"]
    print(newdata)
    with open("database.json", "w") as f:
        json.dump(newdata, f)
    return RedirectResponse("/", 303)


@app.get("/migrate")
def migrate_database(request: Request):

    with open("database.json") as f:
        data = json.load(f)
    try:
        todos_collection.insert_many(
            [{"id": int(k), "description": v} for k, v in data.items()]
        )
        return todos_collection.count_documents({})
    except BulkWriteError as bwe:
        return JSONResponse(
            content={
                "message": f"Partially migrated. {bwe.details['nInserted']} documents inserted.",
                "errors": f"{len(bwe.details['writeErrors'])} errors occurred.",
                "detail": str(bwe.details["writeErrors"]),
            },
            status_code=207,
        )
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


