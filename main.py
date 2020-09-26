from flask import Flask, g, render_template, request, jsonify, redirect
from whois import whois
import sqlite3
import re

app = Flask("app", static_folder="public", template_folder="views")

DATABASE = "shorturls.db"


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


# Initialize database
with app.app_context():
    db = get_db()
    db.cursor().execute("CREATE TABLE IF NOT EXISTS ShortUrl (url TEXT)")
    db.commit()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/shorturl/new", methods=["POST"])
def submit_short_url():
    url = request.form["url"]

    # Check for valid protocol
    protocol_match = re.search("^https?://(.*)", url, flags=re.IGNORECASE)
    if protocol_match is None:
        return jsonify(error="invalid URL", code=400)

    domain_and_path = protocol_match.group(1)

    # Check for valid domain
    domain_match = re.search(
        "^([\w\-]+\.)+[\w\-]+", domain_and_path, flags=re.IGNORECASE
    )
    if domain_match is None:
        return jsonify(error="invalid URL", code=400)
    domain = domain_match.group(0)
    if whois(domain).domain_name is None:
        return jsonify(error="invalid domain", code=400)

    try:
        db = get_db()
        c = db.cursor()
        c.execute("INSERT INTO ShortUrl(url) VALUES(?)", (url,))
        index = c.lastrowid
        db.commit()
        return jsonify(original_url=url, short_url=index)
    except:
        return jsonify(error="database save error", code=500)


@app.route("/api/shorturl/<index>", methods=["GET"])
def redirect_short_url(index):
    try:
        db = get_db()
        c = db.cursor()
        c.execute("SELECT url FROM ShortUrl WHERE rowid == ?", (int(index),))
        result = c.fetchone()
        if result is None:
            return jsonify(error="no such short URL", code=404)
        url = result[0]
        return redirect(url, 301)
    except ValueError:
        return jsonify(error="no such short URL", code=404)
    except:
        return jsonify(error="database error", code=500)


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
