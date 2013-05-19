from pymongo import Connection

def get_db(request):
    return Connection()['new-wiki-3']

def get_permissions(db, role):
    role = db.roles.find_one({"role": role})
    if role is None:
        return None
    return role['permissions']

def update_page(db, path, content):
    db.pages.find_and_modify(
        query={'path': path},
        update={'$set': {
                "content": content,
                }},
        upsert=True,
        )

    path_parts = path.split("/")[:-1]
    filename = path.split("/")[-1]

    if len(path_parts) == 0:
        operation = {"files": filename}
    else:
        operation = {"folders": path_parts[0]}
    db.directory.find_and_modify(
        query={'folder': ""},
        update={'$addToSet': operation},
        upsert=True,
        )

    for i in range(len(path_parts)):
        if i == len(path_parts) - 1:
            operation = {"files": filename}
        else:
            operation = {"folders": path_parts[i+1]}

        db.directory.find_and_modify(
            query={'folder': path_parts[i]},
            update={'$addToSet': operation},
            upsert=True,
            )
        
import os
import subprocess
import shutil
import tempfile

def init_wiki(db, wiki, initial_content, roles):
    dir = tempfile.mkdtemp()
    for path, content in initial_content.items():
        pardir = os.path.abspath(os.path.join(dir, path.replace("/", os.sep), os.pardir))
        try:
            os.makedirs(pardir)
        except Exception:
            pass
        with open(os.path.join(dir, path.replace("/", os.sep)), 'w') as fp:
            fp.write(content)
        update_page(db, path, content)

    subprocess.check_call(["git", "init", dir])
    subprocess.check_call(["git", "--git-dir=%s" % os.path.join(dir, ".git"),
                           "--work-tree=%s" % dir,
                           "add", "."])
    subprocess.check_call(["git", "--git-dir=%s" % os.path.join(dir, ".git"),
                           "--work-tree=%s" % dir,
                           "commit", "-m", "Creating wiki"])
    try:
        os.makedirs(
            os.path.abspath(os.path.join(wiki, os.pardir)))
    except Exception:
        pass
    shutil.move(os.path.join(dir, ".git"), wiki)
    
    subprocess.check_call(["git", "--git-dir=%s" % wiki,
                           "config", "core.bare", "true"])
    
    for role, permissions in roles.items():
        db.roles.insert({"role": role,
                         "permissions": permissions})
