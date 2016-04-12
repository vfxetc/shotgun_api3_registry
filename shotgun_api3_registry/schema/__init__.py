import os
import urlparse


def load_cached(schema, base_url):
    parsed = urlparse.urlparse(base_url)
    name = parsed.netloc or parsed.path
    path = os.path.abspath(os.path.join(__file__, '..', 'cache', '%s.json' % name))
    if os.path.exists(path):
        schema.load(path)
        raise StopIteration()


def load(schema, base_url):
    parsed = urlparse.urlparse(base_url)
    name = parsed.netloc or parsed.path
    path = os.path.abspath(os.path.join(__file__, '..', 'config', name))
    if os.path.exists(path):
        print '    ' + path
        schema.load_directory(path)

