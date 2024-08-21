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
    result = todos_collection.delete_one({"id": int(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Todo not found")
    return RedirectResponse("/", 303)


@app.post("/add")
async def add_todo(request: Request):
    formdata = await request.form()
    new_id = todos_collection.count_documents({}) + 1
    new_todo = {"id": new_id, "description": formdata["newtodo"]}
    try:
        todos_collection.insert_one(new_todo)
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
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
