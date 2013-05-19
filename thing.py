import db

content = {"project-home": "This is a first page", "sub/path": "You can put things in subpaths too."}

def create_form(request):
    json = request.json
    db.init_wiki(db.Connection()[json['wiki']], json['wiki'], content, json['roles'])
    return 
