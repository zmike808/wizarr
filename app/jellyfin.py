import requests
import datetime
from app import *
from flask import abort, jsonify, render_template, redirect
import logging
import re

API_KEY = Settings.get_or_none(Settings.key == "api_key").value if Settings.get_or_none(
    Settings.key == "api_key") else None
JELLYFIN_URL = Settings.get_or_none(Settings.key == "server_url").value if Settings.get_or_none(
    Settings.key == "server_url") else None


def Post(path, data):

    headers = {
        "X-Emby-Token": API_KEY,
    }
    response = requests.post(
        f"{JELLYFIN_URL}{path}", json=data, headers=headers)
    logging.info(f"POST {path} {str(response.status_code)}")
    return response


def Get(path):

    headers = {
        "X-Emby-Token": API_KEY,
    }
    return requests.get(f"{JELLYFIN_URL}{path}", headers=headers)


def jf_inviteUser(username, password, code, email):
    user = {
        "Name": username,
        "Password": password,
    }
    if Invitations.select().where(Invitations.code == code, Invitations.unlimited == 0):
        Invitations.update(used=True, used_at=datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M"), used_by=username).where(Invitations.code == code).execute()
    else:
        Invitations.update(used_at=datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M"), used_by=username).where(Invitations.code == code).execute()

    response = Post("/Users/New", user)
    logging.info(f"Invited {username} to Jellyfin Server")

    user_id = response.json()["Id"]

    sections = None
    if Invitations.select().where(Invitations.code == code, Invitations.specific_libraries != None):
        sections = list(
            (Invitations.get(Invitations.code == code).specific_libraries).split(", "))

    else:
        sections = list(
            (Settings.get(Settings.key == "libraries").value).split(", "))

    policy = dict(Get(f"/Users/{user_id}").json()["Policy"])
    print("Policy: ", policy)
    policy["EnableAllFolders"] = False
    policy["EnabledFolders"] = sections

    Post(f"/Users/{user_id}/Policy", policy)
    expires = (datetime.datetime.now() + datetime.timedelta(days=int(Invitations.get(code=code).duration)
                                                           )) if Invitations.get(code=code).duration else None

    print(expires)
    Users.create(username=username, email=email,
                 password=password, token=user_id, code=code, expires=expires)
    if Invitations.select().where(Invitations.code == code, Invitations.unlimited == 0):
        Invitations.update(used=True, used_at=datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M"), used_by=email).where(Invitations.code == code).execute()
    else:
        Invitations.update(used_at=datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M"), used_by=email).where(Invitations.code == code).execute()
    return


@app.route('/jf-scan', methods=["POST"])
def jf_scan():
    jellyfin_url = request.args.get('jellyfin_url')
    api_key = request.args.get('jellyfin_api_key')
    if not jellyfin_url or not api_key:
        logging.error("Jellyfin URL or API Key not set")
        abort(400)
    try:
        headers = {
            "X-Emby-Token": api_key,
        }
        response = requests.get(
            f"{jellyfin_url}/Library/MediaFolders", headers=headers)
    except Exception as e:
        logging.error(f"Error getting Jellyfin Libraries: {str(e)}")
        abort(400)
    libraries = {
        library["Name"]: library["Id"] for library in response.json()["Items"]
    }
    return jsonify(libraries)


@app.route('/jf-scan-specific', methods=["POST"])
def jf_scan_specific():
    jellyfin_url = JELLYFIN_URL
    api_key = API_KEY
    if not jellyfin_url or not api_key:
        abort(400)
    try:
        response = Get("/Library/MediaFolders")
        libraries_raw = response.json()
    except Exception as e:
        logging.error(f"Error getting Jellyfin Libraries: {str(e)}")
        abort(400)
    libraries = {
        library["Name"]: library["Id"] for library in response.json()["Items"]
    }
    return jsonify(libraries)


@app.route('/setup/open-Jellyfin', methods=["GET"])
def open_jellyfin():
    return redirect(JELLYFIN_URL)


@app.route('/setup/jellyfin', methods=["POST"])
def join_jellyfin():
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm-password')
    code = request.form.get('code')
    email = request.form.get("email")

    if not (re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', email)):
        return render_template("welcome-jellyfin.html", username=username, email=email, code=code, error="Invalid email addres")

    if not username or not password or not code or not email:
        return render_template("welcome-jellyfin.html", username=username, email=email, code=code, error="Please fill out all fields")

    # check password validity
    if len(password) < 8 or len(password) > 20:
        return render_template("welcome-jellyfin.html", username=username, email=email, code=code, error="Password must be between 8 and 20 characters")

    if password != confirm_password:
        return render_template("welcome-jellyfin.html", username=username, email=email, code=code, error="Passwords do not match")
    if not Invitations.select().where(Invitations.code == code, Invitations.expires >= datetime.datetime.now()).exists():
        return render_template("welcome-jellyfin.html", username=username, email=email, code=code, error="Invalid code")
    if Users.select().where(Users.username == username).exists():
        return render_template("welcome-jellyfin.html", username=username, email=email, code=code, error="User already exists")
    if Users.select().where(Users.email == email).exists():
        return render_template("welcome-jellyfin.html", username=username, email=email, code=code, error="Email already exists")
    jf_inviteUser(username, password, code, email)
    return redirect('/setup')


def jf_GetUsers():
    response = Get("/Users")
    # Compare user to database
    for user in response.json():
        if not Users.select().where(Users.token == user["Id"]).exists():
            Users.create(username=user["Name"], email="empty",
                         code="empty", password="empty", token=user["Id"])

    # Compare database to users
    if Users.select():
        for user in Users.select():
            if all(d['Id'] != user.token for d in response.json()):
                user.delete_instance()
    return response.json()


def jf_DeleteUser(user):
    headers = {
        "X-Emby-Token": API_KEY,
    }
    return requests.delete(f"{JELLYFIN_URL}/Users/{user}", headers=headers)
