import json
import random

adjectives ="""autumn hidden bitter misty silent empty dry dark summer
icy delicate quiet white cool spring winter patient
twilight dawn crimson wispy weathered blue billowing
broken cold damp falling frosty green long late lingering
bold little morning muddy old red rough still small
sparkling thrumming shy wandering withered wild black
young holy solitary fragrant aged snowy proud floral
restless divine polished ancient purple lively nameless""".split()

nouns = """waterfall river breeze moon rain wind sea morning
snow lake sunset pine shadow leaf dawn glitter forest
hill cloud meadow sun glade bird brook butterfly
bush dew dust field fire flower firefly feather grass
haze mountain night pond darkness snowflake silence
sound sky shape surf thunder violet water wildflower
wave water resonance sun log dream cherry tree fog
frost voice paper frog smoke star""".split()

def handle(req, syscall):
    org = 'cos316'
    # First, read the class-specific assignment configuration file,
    # including names of existing asignments and their group sizes.
    l_class = syscall.new_dclabel([[org]], [[org]])
    assignments = json.loads(syscall.fs_read([l_class, 'assignments']))
    if req["assignment"] not in assignments:
        return { 'error': 'No such assignment' }

    users = set(req['users'])
    group_size = (assignment["assignment"]["group_size"] or 1)
    if len(users) != group_size:
        return { 'error': 'This assignment requires a group size of %d, given %d.' % (group_size, len(users)) }

    for user in users:
        repo = syscall.fs_read([l_class, req["assignment"], user])
        if repo:
            return {
                'error': ("%s is already completing %s at %s" % (user, req['assignment'], repo.decode('utf-8')))
            }

    resp = None
    name = None
    for i in range(0, 3):
        name = '-'.join([req["assignment"], random.choice(adjectives), random.choice(nouns)])
        api_route = "/repos/%s/%s/generate" % (org, assignments[req["assignment"]]["starter_code"])
        body = {
                'owner': org,
                'name': name,
                'private': True
        }
        resp = syscall.github_rest_post(api_route, body, token);
        if resp.status == 201:
                break
        elif i == 2:
            return { 'error': "Can't find a unique repository name", "status": resp.status }

    for user in req['gh_handles']:
        api_route = "/repos/%s/%s/collaborators/%s" % (org, name, user)
        body = {
            'permission': 'push'
        }
        resp = syscall.github_rest_put(api_route, body, token);
        if resp.status > 204:
            return { 'error': "Couldn't add user to repository", "status": resp.status }

    orig_label = syscall.get_current_label()
    syscall.declassify_to(syscall.public_dclabel().secrecy)
    l_repo = syscall.new_dclabel([['-'.join([org, name])]], [[org]])
    meta_path = [l_repo, '_meta']
    workflow_path = [l_repo, '_workflow']
    syscall.fs_createfile(meta_path)
    syscall.fs_createfile(workflow_path)
    syscall.fs_write(meta_path,
                      bytes(json.dumps({
                          'assignment': req['assignment'],
                          'users': list(users),
                      }), 'utf-8'))
    syscall.fs_write(workflow_path,
                      bytes(json.dumps(["go_grader", "grades", "generate_report", "post_comment"]), 'utf-8'))
    syscall.taint(orig_label)

    for user in users:
        syscall.fs_createdir([l_class, req['assignment']])
        syscall.fs_createfile([l_class, req['assignment'], user])
        syscall.fs_write([l_class, req['assignment'], user],
                          bytes("%s/%s" % (org, name), 'utf-8'))

    return { 'name': name, 'users': list(users), 'github_handles': req['gh_handles'] }
