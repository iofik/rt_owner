#!/usr/bin/env python
import functools
import json
import re
import requests
import sys


conf = {
    'user': 'viofik_liveintent',
    'password': '***',
    'url': 'https://www.iponweb.net/rt/REST/1.0/',
    'queue': 'liveintent',
    'file': re.sub(r'\.py$', '.conf', __file__),
}


def rt_get(req, params=None, method=requests.get, **kwds):
    r = method(conf['url'] + req, params=params,
               auth=(conf['user'], conf['password']), **kwds)
    if not r.ok:
        raise Exception("RT API response: " + r.reason)

    lines = r.text.splitlines()
    if not re.match("RT/[0-9.]+ 200 Ok$", lines[0]):
        raise Exception("Bad response status: " + lines[0])
    if lines[1]:
        raise Exception("Expected empty string, found: " + lines[1])

    return lines[2:]


def rt_post(req, data, **kwds):
    return rt_get(req, method=requests.post, data=data, **kwds)


def parse_tickets_list(lines):
    lines = iter(lines)
    line = next(lines)
    if line != "id\tCF.{Tags}":
        raise Exception("Unexpected response header: " + line)

    tickets = {}
    for line in lines:
        tid, tags = line.split('\t')
        out_tags = []
        owner = None
        for tag in tags.split(','):
            if tag.startswith('@'):
                owner = tag[1:]
            else:
                out_tags.append(tag)
        if owner:
            tickets[tid] = {
                'owner': owner,
                'tags': ','.join(out_tags),
            }

    return tickets


def get_tickets():
    params = {
        'query': "Queue='%s' AND 'CF.{Tags}' LIKE '@'" % conf['queue'],
        'fields': "CF.{Tags}",
        'format': "s",
    }
    lines = rt_get('search/ticket', params)
    return parse_tickets_list(filter(None, lines))


@functools.lru_cache(maxsize=None)
def find_user(user):
    res = rt_get('user/' + user, {'fields': 'Name'})
    try:
        res.index('Name: ' + user)
        return user
    except ValueError:
        pass

    if not user.endswith('_' + conf['queue']):
        return find_user(user + '_' + conf['queue'])


def update_owners():
    for tid, value in get_tickets().items():
        owner = find_user(value['owner'])
        if owner:
            sys.stdout.write("%s -> %s\n" % (tid, owner))
            data = "Owner: %s\nCF.{Tags}: %s\n" % (owner, value['tags'])
        else:
            sys.stdout.write("%s -> %s -- user not found!\n"
                             % (tid, value['owner']))
            data = "CF.{Tags}: %s\n" % (value['tags'])
        rt_post('ticket/%s/edit' % tid, data)


def main():
    try:
        with open(conf['file']) as f:
            jconf = json.load(f)
        conf.update(jconf)
    except FileNotFoundError:
        pass
    update_owners()


if __name__ == '__main__':
    main()
