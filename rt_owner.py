#!/usr/bin/env python
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
    return r.text


def rt_post(req, data, **kwds):
    return rt_get(req, method=requests.post, data=data, **kwds)


def parse_tickets_list(lines):
    lines = iter(lines)
    line = next(lines)
    if not re.match("RT/[0-9.]+ 200 Ok$", line):
        raise Exception("Unexpected response status: " + line)
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
    text = rt_get('search/ticket', params)
    return parse_tickets_list(filter(None, text.split('\n')))


def rt_set_owner(tid, owner, tags):
    data = "Owner: %s\nCF.{Tags}: %s\n" % (owner, tags)
    return rt_post('ticket/%s/edit' % tid, data)


def update_owners():
    for tid, value in get_tickets().items():
        sys.stdout.write("%s -> %s\n" % (tid, value['owner']))
        rt_set_owner(tid, value['owner'], value['tags'])


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
