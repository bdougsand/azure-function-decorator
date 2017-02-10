from datetime import datetime
import glob
import json
import os
import sys
import traceback

try:
    from urllib.parse import parse_qsl
except ImportError:
    from urlparse import parse_qsl

try:
    # Add zipped packages to the same directory where this file lives:
    zip_paths = glob.glob(os.path.join(os.path.dirname(__file__), "*.zip"))
    sys.path += zip_paths
except:
    pass


class Request(object):
    def __init__(self, method="GET", headers=None, query=None, path="/", body=None, out=None):
        self._headers = headers or {}
        self._query = query or {}
        self._post_params = self._process_post_body()
        self._path = path
        self._body = body
        self._method = method
        self._out = out

    @property
    def content_type(self):
        self._headers.get("content-type", "application/x-www-form-urlencoded")

    def read_body(self):
        if not getattr(self, "_bodytext"):
            self._bodytext = self._body.read()
        return self._bodytext

    def _process_post_body(self):
        if self.content_type == "application/x-www-form-urlencoded":
            return dict(parse_qsl(self.read_body()))

        return {}

    @property
    def headers(self):
        return self._headers

    @property
    def GET(self):
        return self._query

    @property
    def POST(self):
        return self._post_params

    def __getitem__(self, k):
        return self._post_params.get(k) or self._query.get(k)

    def write(self, s):
        if self._out:
            self._out.write(s)


def make_request(env):
    headers = {}
    query = {}
    for key, val in env.items():
        if key.startswith("REQ_HEADERS"):
            headers[key[12:].lower()] = val
        elif key.startswith("REQ_QUERY"):
            query[key[10:].lower()] = val

    inpath = env.get("req")
    infile = open(inpath, "r") if inpath else None

    outpath = env.get("res")
    outfile = open(outpath, "w") if outpath else sys.stdout

    return Request(method=env["REQ_METHOD"].upper(),
                   headers=headers,
                   query=query,
                   path=env["REQ_HEADERS_X-ORIGINAL-URL"],
                   body=infile,
                   out=outfile)


def json_serialize(x):
    if isinstance(x, datetime):
        return x.isoformat()

    return str(x)


def output(req, resp):
    req.write(json.dumps(resp, default=json_serialize))


def body_output(req, s, status=200, content_type="text/plain"):
    output(req, {"status": status,
                 "body": s,
                 "headers": {"content-type": content_type}})

def redirect_output(req, location):
    output(req, {"status": 302,
                 "headers": {"location": location}})


def redirect(location):
    return lambda req: redirect_output(req, location)


def azure(fn):
    def do_run():
        req = make_request(os.environ)
        try:
            response = fn(req)

            if isinstance(response, str):
                body_output(req, response)
            elif isinstance(response, dict):
                body_output(req, response, content_type="application/json")
            elif callable(response):
                response(req)
        except Exception as exc:
            body_output(req, traceback.format_exc(), status=500)

    return do_run
