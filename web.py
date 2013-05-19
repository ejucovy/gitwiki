import os
import shutil
import subprocess
from tempfile import mkdtemp
import uuid

from utils import allow_http, require_permission

def dispatcher(request):
    path = request.path
    if path.endswith("/edit/"):
        resp = edit(request, path[:-6].lstrip("/"))
    elif path.endswith("/commit/"):
        resp = commit(request, path[:-8].lstrip("/"))
    elif path.endswith("/save/"):
        resp = save(request, path[:-6].lstrip("/"))
    elif path.startswith("/dir/"):
        resp = directory(request, path[5:].strip("/"))
    else:
        resp = view(request, path.strip("/"))
    return resp

@allow_http("GET")
@require_permission("view")
def directory(request, path):
    contents = request.db.directory.find_one({"folder": path})
    return """<html>
<body>
<h2>Folders</h2>
%s
<h2>Files</h2>
%s
</body>
</html>""" % ("".join('<div><a href="/dir/{path}/{entry}">{entry}</a></div>'.format(path=path,
                                                                                   entry=entry) 
                      for entry in contents.get('folders', [])),
              "".join('<div><a href="/{path}/{entry}">{entry}</a></div>'.format(path=path,
                                                                                entry=entry) 
                      for entry in contents.get('files', [])))
@allow_http("GET")
@require_permission("view")
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
@require_permission("edit")
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

  <input type="submit" formaction="/{path}/commit/" value="Save and continue editing" />
  <input type="submit" value="Save" />
</form>
</body>
</html>
""".format(content=content, uid=uid, path=path)

@allow_http("POST")
@require_permission("edit")
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
                                                            "Work in progress"),
                           "--author", "%s <>" % request.username])
    subprocess.check_call(["git", "--git-dir=%s" % os.path.join(checkout_path, ".git"),
                           "--work-tree=%s" % checkout_path,
                           "push", "origin", "%s/%s" % (request.username, checkout['id'])])

    return "ok"

@allow_http("POST")
@require_permission("edit")
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
                           "commit", "-m", request.POST['commit_message'],
                           "--author", "%s <>" % request.username])

    subprocess.check_call(["git", "--git-dir=%s" % os.path.join(checkout_path, ".git"),
                           "--work-tree=%s" % checkout_path,
                           "push", "--all"])

    shutil.rmtree(checkout_path)
    request.db.checkouts.remove(checkout)

    update_page(request.db, path, request.POST['content'])
    return "ok"
