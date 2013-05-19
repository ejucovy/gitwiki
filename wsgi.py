from webob import Request, Response
import web as views
from db import get_db, get_permissions

import thing

def make_application(user_getter, context_getter):
    def application(environ, start_response):
        request = Request(environ)

        if request.path == "/_create/":
            thing.create_form(request)
            return Response("ok")(environ, start_response)

        user_getter(request)
        context_getter(request)
        request.permissions = get_permissions(request.db, request.role)
        resp = views.dispatcher(request)
        
        return Response(resp)(environ, start_response)
    return application

def sample_user_getter(request):
    request.username = "bob"
    request.role = "ProjectAdmin"

def sample_context_getter(request):
    request.wiki = "/tmp/our33/new/wiki"
    request.db = get_db(request)

if __name__ == '__main__':
    from paste.httpserver import serve
    application = make_application(sample_user_getter, sample_context_getter)
    serve(application, port='8080')
