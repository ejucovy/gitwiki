from pymongo import Connection

def get_db(request):
    return Connection()['gitwiki']


