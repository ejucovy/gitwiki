import envoy
import os
import shutil
import subprocess
from tempfile import mkdtemp
import uuid

from utils import allow_http

@allow_http("GET")
def view(request, path):
    pass

@allow_http("GET")
def edit(request, path):
    origin = request.wiki
    checkout = mkdtemp(prefix="gitwiki-") # @@TODO a wiki-specific prefix

    cwd = os.getcwd()
    os.chdir(checkout)
    try:
        subprocess.check_call(["git", "init"])
        subprocess.check_call(["git", "remote", "add", "origin", origin])
        subprocess.check_call(["git", "fetch", "--depth", "1", "origin"])
        subprocess.check_call(["git", "config", "core.sparseCheckout", "true"])
        with open(os.path.join(checkout, 
                               ".git", "info", 
                               "sparse-checkout"),
                  'w') as fp:
            fp.write(path)
        subprocess.check_call(["git", "checkout", "master"])
    finally:
        os.chdir(cwd)

    with open(os.path.join(checkout, path.replace("/", os.sep))) as fp:
        content = fp.read()

    uid = uuid.uuid4().hex

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
</body>
</html>
""".format(content=content, uid=uid, path=path)

@allow_http("POST")
def save(request, path):
    checkout = request.db.checkouts.find_one({
            "user": request.username,
            "id": request.POST['checkout'],
            })

    checkout_path = checkout['checkout']
    with open(os.path.join(checkout_path, path.replace("/", os.sep)), 'w') as fp:
        fp.write(request.POST['content'])

    cwd = os.getcwd()
    os.chdir(checkout_path)
    
    try:
        subprocess.check_call(["git", "add", path.replace("/", os.sep)])
        subprocess.check_call(["git", "commit", "-m", request.POST['commit_message']])
        subprocess.check_call(["git", "push"])
    finally:
        os.chdir(cwd)

    shutil.rmtree(checkout_path)
    request.db.checkouts.remove(checkout)
    return "ok"
