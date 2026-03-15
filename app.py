from flask import Flask, request, Response, render_template, jsonify
import requests
import json
import os
from duckduckgo_search import DDGS
import PyPDF2

app = Flask(__name__)

OLLAMA="http://127.0.0.1:11434/api/chat"

history={}

def search(query):

    results=[]

    with DDGS() as ddgs:
        for r in ddgs.text(query,max_results=3):
            results.append(r["body"])

    return "\n".join(results)


def read_pdf(file):

    reader=PyPDF2.PdfReader(file)

    text=""

    for p in reader.pages:
        t=p.extract_text()
        if t:
            text+=t

    return text[:3000]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat",methods=["POST"])
def chat():

    data=request.json
    msg=data["message"]
    chat_id=data["chat"]

    if chat_id not in history:
        history[chat_id]=[]

    # поиск
    if msg.startswith("search:"):

        q=msg.replace("search:","")

        info=search(q)

        msg=f"Используй эту информацию:\n{info}\n\nВопрос:{q}"

    history[chat_id].append({
        "role":"user",
        "content":msg
    })

    r=requests.post(
        OLLAMA,
        json={
            "model":"llama3",
            "messages":history[chat_id],
            "stream":True
        },
        stream=True
    )

    def generate():

        full=""

        for line in r.iter_lines():

            if line:

                data=json.loads(line.decode())

                if "message" in data:

                    token=data["message"]["content"]

                    full+=token

                    yield token

        history[chat_id].append({
            "role":"assistant",
            "content":full
        })

    return Response(generate(),mimetype="text/plain")


@app.route("/upload",methods=["POST"])
def upload():

    file=request.files["file"]

    text=read_pdf(file)

    return jsonify({"text":text})


if __name__=="__main__":
    app.run(debug=True)