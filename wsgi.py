from webob import Request, Response
import web as views
from db import get_db

def application(environ, start_response):
    request = Request(environ)
    request.db = get_db(request)
    request.username = "bob"
    request.wiki = "/tmp/my-wiki"

    path = request.path

    if path.endswith("/edit/"):
        resp = views.edit(request, path[:-6].lstrip("/"))
    elif path.endswith("/save/"):
        resp = views.save(request, path[:-6].lstrip("/"))
    else:
        resp = views.view(request, path)

    return Response(resp)(environ, start_response)

if __name__ == '__main__':
    from paste.httpserver import serve
    serve(application, port='8080')
