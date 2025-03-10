from bson import ObjectId
from flask import Flask, render_template, url_for, request, redirect, session
from pymongo import MongoClient

Client = MongoClient('localhost', 27017)

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('login.html')


@app.route('/register')
def register():
    return render_template('register.html')


db = Client.SchoolManagement
students = db.students

if __name__ == '__main__':
    app.run()
