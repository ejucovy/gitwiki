
def allow_http(*methods):
    def _allow_http(view):
        def inner(request, *args, **kw):
            if request.method in methods:
                return view(request, *args, **kw)
            return "Method not allowed"
        inner.__name__ = view.__name__
        return inner
    return _allow_http

            
