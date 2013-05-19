
def allow_http(*methods):
    def _allow_http(view):
        def inner(request, *args, **kw):
            if request.method in methods:
                return view(request, *args, **kw)
            return "Method not allowed"
        inner.__name__ = view.__name__
        return inner
    return _allow_http

def require_permission(*permissions):
    def _require_permission(view):
        def inner(request, *args, **kw):
            for permission in permissions:
                if permission not in request.permissions:
                    return "You can't do that!"
            return view(request, *args, **kw)
        inner.__name__ = view.__name__
        return inner
    return _require_permission
