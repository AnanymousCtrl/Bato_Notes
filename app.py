from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from flask_pymongo import PyMongo
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
import os
import bcrypt

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/notesDB"

app.secret_key = "YELO_0119"

mongo = PyMongo(app)

##folder to store uploads
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


@app.route("/register", methods= ['GET','POST'])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        users = mongo.db.users
        existing_user = users.find_one({"username": username})

        if existing_user:
            flash("Username already exists!", "danger")
            return redirect(url_for("register"))

        hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        users.insert_one({"username": username, "password": hashed_pw})

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        users = mongo.db.users
        user = users.find_one({"username": username})

        if user and bcrypt.checkpw(password.encode("utf-8"), user["password"]):
            session["user_id"] = str(user["_id"])
            flash("Login Successful!", "success")
            return redirect(url_for("index"))

        flash("Invalid username or password", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged Out Successfully!", "success")
    return redirect(url_for("login"))

@app.route("/", methods=["GET"])
def index():
    search_query = request.args.get("search", "")
    notes = mongo.db.notes.find({"subject": {"$regex": search_query, "$options": "i"}})
    return render_template("index.html", notes=notes)

@app.route("/upload", methods = ["GET", "POST"])
def upload():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        subject = request.form["subject"]
        file = request.files["file"]

        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            mongo.db.notes.insert_one({"subject": subject, "file_path": filepath, "download": 0})
            flash("Notes uploaded successfully!", "success")
            return redirect(url_for("index"))
    
    return render_template("upload.html")

@app.route("/download/<note_id>")
def download(note_id):
    note = mongo.db.notes.find_one({"_id": ObjectId(note_id)})

    if note:
        mongo.db.notes.update_one({"_id": ObjectId(note_id)}, {"$inc": {"download": 1}})
        return send_from_directory(app.config["UPLOAD_FOLDER"], os.path.basename(note["file_path"]), as_attachment = True)
    
    flash("note not found!", "danger")
    return redirect(url_for("index"))

@app.route("/note/<note_id>", methods=["GET", "POST"])
def view_note(note_id):
    note = mongo.db.notes.find_one({"_id": ObjectId(note_id)})
    comments = list(mongo.db.comments.find({"note_id": note_id}))

    if request.method == "POST" and "user_id" in session:
        content = request.form["content"]
        mongo.db.comments.insert_one({"note_id": note_id, "user_id": session["user_id"], "content": content})
        flash("Comment Added!", "success")
        return redirect(url_for("view_note", note_id=note_id))
    
    return render_template("note.html", note=note, comments=comments)


if __name__ == "__main__":
    app.run(debug=True)