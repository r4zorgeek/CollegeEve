from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
from datetime import datetime
from cs50 import SQL
from flask_jsglue import JSGlue
from helpers import *

import sys

# app configuration
app = Flask(__name__)
JSGlue(app)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///project.db")

@app.route("/")
def index():
    """ Display Colleges with theirs events. """

    print(request.environ["REMOTE_ADDR"], file=sys.stderr)

    # list to send data to index page
    send = list()

    rows = db.execute("SELECT clg_name, event_name, eve_date \
                       FROM registrants \
                       JOIN clg_event ON clg_event.clg_id = registrants.college_id \
                       JOIN clg_list ON registrants.college_id = clg_list.id")

    for data in rows:
        send.append({'clg_name': data["clg_name"], 'eve_name': data["event_name"], 'eve_date': data["eve_date"]})
        # print(data, file=sys.stderr)

    return render_template("index.html", clg=send)

@app.route("/register", methods=["POST", "GET"])
def register():
    """ Register User in Database. """

    # ensure if user reached via route GET
    if request.method == "GET":
        return render_template("register.html")

    else:
        email_id = request.form.get("email_id")
        passw = request.form.get("password")
        clg_name = request.form.get("college_name")

        # search for clg_id
        rows = db.execute("SELECT id FROM clg_list WHERE clg_list MATCH :q", q = clg_name)
        if not rows:
            return apology('College Name Not Found')
        cl_id = rows[0]['id']

        # insert into register table (Register User)
        rows_t = db.execute("INSERT INTO registrants (email_id, hash, college_id) VALUES (:em, :hash, :clg_id)", em=email_id, hash=pwd_context.hash(passw), clg_id = cl_id)
        if not rows_t:
            return apology("User Already Registered!")

        else:
            session["clg_id"] = cl_id
            return redirect(url_for('portfolio'))



@app.route('/search')
def search():
    """ Search for Colleges that match query. """

    # search query
    print("{}".format(request.args.get('q')), file=sys.stderr)

    # query for college names
    query = request.args.get('q')

    # search database for college name according to query
    rows = db.execute("SELECT clg_name FROM clg_list WHERE clg_list MATCH :q", q = query)

    if not rows:
        return jsonify([])

    return jsonify([clg_name for clg_name in rows])

    return jsonify([])


@app.route("/login", methods=["GET", "POST"])
def login():
    """ Login User. """

    # forget any clg_id
    session.clear()

    # ensure if user reached via route GET
    if request.method == "GET":
        return render_template("login.html")

    else:

        # check if credentials are valid
        email_id = request.form.get('email_id')
        passw = request.form.get('password')

        result = db.execute("SELECT * FROM registrants WHERE email_id = :e", e = email_id)
        if len(result) != 1 or not pwd_context.verify(passw, result[0]['hash']):
            return apology('Invalid USERNAME/PASSWORD')

        # get college id
        rows = db.execute("SELECT college_id FROM registrants WHERE email_id = :e", e = request.form.get('email_id'))
        if not rows:
            return apology("Error")

        else:
            session["clg_id"] = rows[0]['college_id']
            return redirect(url_for('portfolio'))


@app.route("/portfolio", methods=["GET", "POST"])
@login_required
def portfolio():
    """ All The Events of Logedin User. """

    # list to send data to index page
    send = list()

    rows = db.execute("SELECT clg_name, event_name, eve_date \
                       FROM registrants \
                       JOIN clg_event ON clg_event.clg_id = registrants.college_id \
                       JOIN clg_list ON registrants.college_id = clg_list.id \
                       WHERE clg_event.clg_id = :q", q = session["clg_id"])

    for data in rows:
        send.append({'clg_name': data["clg_name"], 'eve_name': data["event_name"], 'eve_date': data["eve_date"]})


    return render_template('portfolio.html', clg=send)


@app.route("/logout")
def logout():

    # clear Collge id
    session.clear()

    return redirect(url_for('index'))


@app.route('/addEvent', methods=["POST"])
@login_required
def addEvent():
    """ Add Event to the portfolio. """

    if request.method == "POST":
        # get event name and event date
        eve_name = request.form.get('eve_name')
        eve_date = request.form.get('eve_date')

        # insert into event list table
        result = db.execute("INSERT INTO clg_event (clg_id, event_name, eve_date)\
                             VALUES (:cid, :ename, :edate)", cid=session["clg_id"], ename=eve_name, edate=eve_date)

        if not result:
            return apology('Error')

        return redirect(url_for('portfolio'))


@app.route('/search_for_clg', methods=["GET", "POST"])
def search_for_clg():

    if request.method == "POST":
        #query
        clg_name = request.form.get('college_name')

        print(clg_name, file=sys.stderr)

        # list to send data to page
        send = list()

        # search for clg_id
        rows = db.execute("SELECT id FROM college_list WHERE clg_name = :q", q = clg_name)
        if not rows:
            return apology('College Name Not Found')

        rows_t = db.execute("SELECT clg_name, event_name, eve_date \
                             FROM registrants \
                             JOIN clg_event ON clg_event.clg_id = registrants.college_id \
                             JOIN clg_list ON registrants.college_id = clg_list.id \
                             WHERE clg_event.clg_id = :q", q = rows[0]['id'])

        if not rows_t:
            return apology("No Event For This College")

        else:
            for data in rows_t:
                send.append({'clg_name': data["clg_name"], 'eve_name': data["event_name"], 'eve_date': data["eve_date"]})

        return render_template("index.html", clg=send)


@app.route("/removeEvent", methods=["POST", "GET"])
@login_required
def removeEvent():
    # ensure if user reached via route GET
    if request.method == "GET":
        # list to send data to index page
        send = list()

        rows = db.execute("SELECT event_name, eve_date \
                           FROM registrants \
                           JOIN clg_event ON clg_event.clg_id = registrants.college_id \
                           JOIN clg_list ON registrants.college_id = clg_list.id \
                           WHERE clg_event.clg_id = :q", q = session["clg_id"])

        for data in rows:
            send.append({'eve_name': data["event_name"], 'eve_date': data["eve_date"]})


        return render_template("remove_events.html", event_list=send)

    # if user reached via route POST
    else:
        # get names of events to be removed
        eve_names = list(dict(request.form)["event_name"])

        for name in eve_names:
            result = db.execute("DELETE FROM clg_event WHERE event_name = :q AND clg_id = :c", q = name, c = session["clg_id"])
            if not result:
                return redirect(url_for('portfolio'))

        return redirect(url_for('portfolio'))
