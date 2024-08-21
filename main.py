from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import json
import pymongo

app = FastAPI()
templates = Jinja2Templates(directory="templates")
client = pymongo.MongoClient("localhost", 27017)


@app.get("/")
async def root(request: Request):
    with open("database.json") as f:
        data = json.load(f)
    return templates.TemplateResponse(
        "todolist.html", {"request": request, "tododict": data}
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

    db = client.warmly
    todos = db.todos
    with open("database.json") as f:
        data = json.load(f)
    try:
        todos.insert_many([{k: v} for k, v in data.items()])

        return todos.count_documents({})
    except Exception as ex:

        return {"error": str(ex)}
