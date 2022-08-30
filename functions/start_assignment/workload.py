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
    course = req["course"]
    assignments = json.loads(syscall.read_key(bytes(f'{course}/assignments', "utf-8")))
    if req["assignment"] not in assignments:
        return { 'error': 'No such assignment' }

    users = set(req['users'])
    assignment = assignments[req["assignment"]]
    enrollments = json.loads(syscall.read_key(bytes(f'{course}/enrollments.json', 'utf-8')) or "{}")

    for user in users:
        if not enrollments.get(user):
            return { 'error': 'Only enrolled students may create assignments', 'user': user, 'course': course }

    group_size = (assignment["group_size"] or 1)
    if len(users) != group_size:
        return { 'error': 'This assignment requires a group size of %d, given %d.' % (group_size, len(users)) }

    for user in users:
        repo = syscall.read_key(bytes('%s/assignments/%s/%s' % (course, req["assignment"], user), 'utf-8'));
        if repo:
            return {
                'error': ("%s is already completing %s at %s" % (user, req['assignment'], repo.decode('utf-8')))
            }

    resp = None
    name = None
    for i in range(0, 3):
        name = '-'.join([req["assignment"], random.choice(adjectives), random.choice(nouns)])
        api_route = "/repos/%s/generate" % (assignments[req["assignment"]]["starter_code"])
        body = {
                'owner': course,
                'name': name,
                'private': True
        }
        resp = syscall.github_rest_post(api_route, body);
        if resp.status == 201:
                break
        elif i == 2:
            return { 'error': "Can't find a unique repository name", "status": resp.status }

    for user in req['gh_handles']:
        api_route = "/repos/%s/%s/collaborators/%s" % (course, name, user)
        body = {
            'permission': 'push'
        }
        resp = syscall.github_rest_put(api_route, body);
        if resp.status > 204:
            return { 'error': "Couldn't add user to repository", "status": resp.status }


    syscall.write_key(bytes('github/%s/%s/_meta' % (course, name), 'utf-8'),
                      bytes(json.dumps({
                          'assignment': req['assignment'],
                          'users': list(users),
                      }), 'utf-8'))
    syscall.write_key(bytes('github/%s/%s/_workflow' % (course, name), 'utf-8'),
                      bytes(json.dumps(f'{course}/{req["assignment"]}/_workflow'), 'utf-8'))
    for user in users:
        syscall.write_key(bytes('%s/assignments/%s/%s' % (course, req["assignment"], user), 'utf-8'),
                          bytes("%s/%s" % (course, name), 'utf-8'))

    return { 'name': name, 'users': list(users), 'github_handles': req['gh_handles'] }
