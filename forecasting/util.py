import re
from urlparse import urlsplit, urlunsplit
import httplib2


def request(url):
    """
    Open a given URL and return headers and body.

    This function retrieves data from a given URL, returning the headers
    and the response body. Authentication can be set by adding the
    username and password to the URL; this will be sent as clear text
    only if the server only supports Basic authentication.

    """
    h = httplib2.Http(cache="/tmp/pydap-cache/")
    scheme, netloc, path, query, fragment = urlsplit(url)
    if '@' in netloc:
        credentials, netloc = netloc.split('@', 1)  # remove credentials from netloc
        username, password = credentials.split(':', 1)
        h.add_credentials(username, password)

    url = urlunsplit((
            scheme, netloc, path, query, fragment
            )).rstrip('?&')

    resp, data = h.request(url, "GET", headers = {
        'user-agent': 'TESTING-AGENT',
        'connection': 'close'})

    # When an error is returned, we parse the error message from the
    # server and return it in a ``ClientError`` exception.
    if resp.get("content-description") in ["dods_error", "dods-error"]:
        m = re.search('code = (?P<code>[^;]+);\s*message = "(?P<msg>.*)"',
                data, re.DOTALL | re.MULTILINE)
        msg = 'Server error %(code)s: "%(msg)s"' % m.groupdict()
        raise Exception(msg)

    return resp, data
