from app import *
import datetime
import logging, logging.config



# Migrations 1
try:
    migrator = SqliteMigrator(database)
    duration = CharField(null=True)  # Add Duration after update
    migrate(
        migrator.add_column('Invitations', 'duration', duration)
    )
except:
    pass


# Migrations 2
try:
    migrator = SqliteMigrator(database)
    specific_libraries = CharField(null=True)  # Add Specific Libraries after update
    migrate(
        migrator.add_column(
            'Invitations', 'specific_libraries', specific_libraries)
    )
except:
    pass

# Migrations 3
try:
    migrator = SqliteMigrator(database)
    expires = DateTimeField(null=True)  # Add Expires after update
    migrate(
        migrator.add_column(
            'Users', 'expires', expires)
    )
except:
    pass


# For all invitations, if the expires is not a string, make it a string
for invitation in Invitations.select():
    if invitation.expires == "None":
        invitation.expires = None
        invitation.save()
    elif type(invitation.expires) == str:
        invitation.expires = datetime.datetime.strptime(
            invitation.expires, "%Y-%m-%d %H:%M")
        invitation.save()


if not os.getenv("APP_URL"):
    logging.error("APP_URL not set or wrong format. See docs for more info.")
    exit(1)

LOGGING_CONFIG = {
    "version": 1,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simple",
        },
    },
    "formatters": {
        "simple": {
            "format": "%(asctime)s - %(levelname)s - %(message)s",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": os.getenv("LOG_LEVEL", "ERROR"),
            "propagate": True,
        },
    },
}

try:
    logging.config.dictConfig(LOGGING_CONFIG)
except:
    logging.critical("Error in logging config, ignoring")

# Migrate from Plex to Global Settings:
if (
    Settings.select().where(Settings.key == 'admin_username').exists()
    and Settings.select().where(Settings.key == 'plex_verified').exists()
    and not Settings.select().where(Settings.key == 'server_type').exists()
):
    try:
        os.system("cp ./database/database.db ./database/1.6.5-database-backup.db")
        logging.info("Database backup created due to major version update.")
    except:
        pass
    Settings.create(key='server_type', value='plex')
    Settings.create(key='api_key', value=Settings.get(Settings.key == 'plex_token').value)
    Settings.delete().where(Settings.key == 'plex_token').execute()
    Settings.create(key='server_url', value=Settings.get(Settings.key == 'plex_url').value)
    Settings.delete().where(Settings.key == 'plex_url').execute()
    Settings.create(key='server_name', value=Settings.get(Settings.key == 'plex_name').value)
    Settings.delete().where(Settings.key == 'plex_name').execute()
    Settings.create(key='libraries', value=Settings.get(Settings.key == 'plex_libraries').value)
    Settings.delete().where(Settings.key == 'plex_libraries').execute()
    Settings.create(key='server_verified', value=Settings.get(Settings.key == 'plex_verified').value)
    Settings.delete().where(Settings.key == 'plex_verified').execute()
            
        