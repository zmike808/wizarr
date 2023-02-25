from app import *
from app.plex import *
from app.jellyfin import *

def GlobalDeleteUser(user):
    server_type = Settings.get(Settings.key == "server_type").value
    if server_type == "plex":
        try:
            deleteUser(user)
        except Exception as e:
            if "429" in str(e):
                logging.error("Too many requests to Plex API")
            else:
                logging.error(f"Unable to delete user: {str(e)}")
    elif server_type == "jellyfin":
        jf_DeleteUser(user)
    


def GlobalGetUsers():
    server_type = Settings.get(Settings.key == "server_type").value
    if server_type == "plex":
        try:
            return getUsers()
        except Exception as e:
            if "429" in str(e):
                logging.error("Too many requests to Plex API")
            else:
                logging.error(f"Unable to get users: {str(e)}")
    elif server_type == "jellyfin":
        try:
            jf_GetUsers()
            return Users.select()
        except Exception as e:
            if "429" in str(e):
                logging.error("Too many requests to Jellyfin API")
            else:
                logging.error(f"Unable to get users: {str(e)}")