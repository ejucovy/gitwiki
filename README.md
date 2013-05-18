A git-based wiki.

Current file contents are cached in a (mongo) database.

Histories are stored in a git repository.

Editing a file looks like:

 1. GET /edit/ form -- clones the repository into a tempdir (shallow and sparse) and checks out a new branch
 2. POST /commit/ -- 'save and continue editing' -- commit the current contents of the file onto the branch
 3. POST /save/ -- checkout master branch, commit the current contents of the file, and push both master and the temporary branch to origin

*shrug*
