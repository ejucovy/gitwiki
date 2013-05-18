import os
import shutil
import subprocess
from tempfile import mkdtemp
import uuid

from utils import allow_http

@allow_http("GET")
def directory(request, path):
    contents = request.db.directory.find_one({"folder": path})
    return str(contents)

@allow_http("GET")
def view(request, path):
    page = request.db.pages.find_one({'path': path})
    if page is None:
        return "None"
    return """<html>
<body>
{content}
</body>
</html>""".format(**page)

@allow_http("GET")
def edit(request, path):
    origin = request.wiki
    checkout = mkdtemp(prefix="gitwiki-") # @@TODO a wiki-specific prefix
    uid = uuid.uuid4().hex

    subprocess.check_call(["git", "--git-dir=%s" % os.path.join(checkout, ".git"),
                           "--work-tree=%s" % checkout,
                           "init"])
    subprocess.check_call(["git", "--git-dir=%s" % os.path.join(checkout, ".git"),
                           "--work-tree=%s" % checkout,
                           "remote", "add", "origin", origin])
    subprocess.check_call(["git", "--git-dir=%s" % os.path.join(checkout, ".git"),
                           "--work-tree=%s" % checkout,
                           "fetch", "--depth", "1", "origin"])
    subprocess.check_call(["git", "--git-dir=%s" % os.path.join(checkout, ".git"),
                           "--work-tree=%s" % checkout,
                           "config", "core.sparseCheckout", "true"])
    with open(os.path.join(checkout, 
                           ".git", "info", 
                           "sparse-checkout"),
              'w') as fp:
        fp.write(path)
    subprocess.check_call(["git", "--git-dir=%s" % os.path.join(checkout, ".git"),
                           "--work-tree=%s" % checkout,
                           "checkout", "master"])
    subprocess.check_call(["git", "--git-dir=%s" % os.path.join(checkout, ".git"),
                           "--work-tree=%s" % checkout,
                           "checkout", "-b", "%s/%s" % (request.username, uid)])
    
    with open(os.path.join(checkout, path.replace("/", os.sep))) as fp:
        content = fp.read()

    request.db.checkouts.insert({
            "user": request.username,
            "id": uid,
            "checkout": checkout,
            })
    
    return """
<html>
<body>
<form method="POST" action="/{path}/save/">
<textarea name="content">{content}</textarea>
<input type="hidden" name="checkout" value="{uid}" />
<input type="text" name="commit_message" />
<input type="submit" />
</form>
<form method="POST" action="/{path}/commit/">
<textarea name="content">{content}</textarea>
<input type="hidden" name="checkout" value="{uid}" />
<input type="text" name="commit_message" />
<input type="submit" value="Save and continue editing" />
</form>
</body>
</html>
""".format(content=content, uid=uid, path=path)

@allow_http("POST")
def commit(request, path):
    checkout = request.db.checkouts.find_one({
            "user": request.username,
            "id": request.POST['checkout'],
            })

    checkout_path = checkout['checkout']
    with open(os.path.join(checkout_path, path.replace("/", os.sep)), 'w') as fp:
        fp.write(request.POST['content'])

    subprocess.check_call(["git", "--git-dir=%s" % os.path.join(checkout_path, ".git"),
                           "--work-tree=%s" % checkout_path,
                           "add", path.replace("/", os.sep)])
    subprocess.check_call(["git", "--git-dir=%s" % os.path.join(checkout_path, ".git"),
                           "--work-tree=%s" % checkout_path,
                           "commit", "-m", request.POST.get('commit_message', 
                                                            "Work in progress")])
    subprocess.check_call(["git", "--git-dir=%s" % os.path.join(checkout_path, ".git"),
                           "--work-tree=%s" % checkout_path,
                           "push", "origin", "%s/%s" % (request.username, checkout['id'])])

    return "ok"

@allow_http("POST")
def save(request, path):
    checkout = request.db.checkouts.find_one({
            "user": request.username,
            "id": request.POST['checkout'],
            })

    checkout_path = checkout['checkout']
    
    subprocess.check_call(["git", "--git-dir=%s" % os.path.join(checkout_path, ".git"),
                           "--work-tree=%s" % checkout_path,
                           "checkout", "master"])
    
    with open(os.path.join(checkout_path, path.replace("/", os.sep)), 'w') as fp:
        fp.write(request.POST['content'])
        
        
    subprocess.check_call(["git", "--git-dir=%s" % os.path.join(checkout_path, ".git"),
                           "--work-tree=%s" % checkout_path,
                           "add", path.replace("/", os.sep)])
    subprocess.check_call(["git", "--git-dir=%s" % os.path.join(checkout_path, ".git"),
                           "--work-tree=%s" % checkout_path,
                           "commit", "-m", request.POST['commit_message']])
    subprocess.check_call(["git", "--git-dir=%s" % os.path.join(checkout_path, ".git"),
                           "--work-tree=%s" % checkout_path,
                           "push", "--all"])

    shutil.rmtree(checkout_path)
    request.db.checkouts.remove(checkout)

    
    request.db.pages.find_and_modify(
            query={'path': path},
            update={'$set': {
                "content": request.POST['content'],
                }},
            upsert=True,
            )
    path_parts = path.split("/")[:-1]
    filename = path.split("/")[-1]

    if len(path_parts) == 0:
        operation = {"files": filename}
    else:
        operation = {"folders": path_parts[0]}
    request.db.directory.find_and_modify(
        query={'folder': ""},
        update={'$addToSet': operation},
        upsert=True,
        )

    for i in range(len(path_parts)):
        if i == len(path_parts) - 1:
            operation = {"files": filename}
        else:
            operation = {"folders": path_parts[i+1]}

        request.db.directory.find_and_modify(
            query={'folder': path_parts[i]},
            update={'$addToSet': operation},
            upsert=True,
            )
    return "ok"
