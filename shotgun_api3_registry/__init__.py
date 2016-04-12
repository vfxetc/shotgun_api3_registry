import logging
import os
import sys
import urllib


# Turn logging down premptively.
logging.getLogger("shotgun_api3").setLevel(logging.WARNING)


import shotgun_api3


_server_names = {
    'production': 'https://example.shotgunstudio.com',
}


_registry = {

    # Production
    'https://example.shotgunstudio.com': {

        # Default fallback if we can't figure it out.
        None: ('general', 'xxx'),

        'sgfs': ('sgfs', 'xxx'),
        'sgcache': ('sgcache', 'xxx'),
        'sgevents': ('sgevents', 'xxx'),
        'sgfs': ('sgfs', 'xxx'),
        'sgpublish': ('sgpublish', 'xxx'),

    },

}


# These are the arguments and defaults for the shotgun_api3 Shotgun constructor.
_default_args = (
    ('base_url', None),
    ('script_name', None),
    ('api_key', None),
    ('convert_datetimes_to_utc', True),
    ('http_proxy', None),
    ('ensure_ascii', True),
    ('connect', True),
    ('ca_certs', None),
    ('login', None),
    ('password', None),
    ('sudo_as_login', None),
    ('session_token', None),
    ('auth_token', None),
)
_default_arg_names = set(x[0] for x in _default_args)


def _args_to_kwargs(args, skip=0):
    if isinstance(args, dict):
        return dict(args)
    kwargs = {}
    for (name, default), value in zip(_default_args[skip:], args):
        if value != default:
            kwargs[name] = value
    return kwargs

def _kwargs_to_args(kwargs):
    args = []
    for name, default in _default_args:
        args.append((name, kwargs.get(name, default)))
    while args and args[-1] == _default_args[len(args) - 1]:
        args.pop(-1)
    return tuple(x[1] for x in args)


def _conform_server(server):
    return os.environ.get('SHOTGUN', 'production') if server is None else server


_sgcache_ping_result = {}
def _ping_sgcache(base_url):
    url = base_url + '/ping'

    try:
        return _sgcache_ping_result[url]
    except KeyError:
        ok = False

        try:
            res = urllib.urlopen(url)
            code = res.getcode()
            body = res.read().strip()
            if code == 200 and body == 'pong':
                ok = True
            elif code != 200:
                logging.getLogger(__name__).warning('sgcache not responding to %s; returned %s' % (url, code))
            else:
                logging.getLogger(__name__).warning('sgcache not responding to %s; returned %s %r' % (url, code, body))

        except IOError as e:
            logging.getLogger(__name__).warning('sgcache not responding to %s: %r' % (url, e))

        _sgcache_ping_result[url] = ok
        return ok



def get_kwargs(name=None, server=None, auto_name_stack_depth=0, use_cache=True, use_envvars=True, **extra):

    # Get the module name that this was called from using stack frame magic.
    if name is None and hasattr(sys, '_getframe'):

        try:
            frame = sys._getframe(1 + auto_name_stack_depth)
        except ValueError:
            pass
        else:
            name = frame.f_globals.get('__name__')

            # Was run via `python -m <name>`; reconstruct the name.
            if name == '__main__':
                package = frame.f_globals.get('__package__')
                file_name = frame.f_code.co_filename
                base_name = file_name and os.path.splitext(os.path.basename(file_name))[0]
                name = '.'.join(x for x in (package, base_name) if x) or None


    # Convert server names into URLs
    server = _conform_server(server)
    server = _server_names.get(server, server).strip('/')

    # Try adding HTTPS
    http_server = 'https://' + server
    if http_server in _registry:
        server = http_server

    kwargs = {}

    try:
        local_registry = _registry[server]
    except KeyError:
        raise ValueError('no %r Shotgun server' % server)

    # Look up config by name.
    # Start at the most precise and keep going to the most general.
    # E.g. 'a.b.c' will try 'a.b.c', then 'a.b', then 'a'.
    if name is not None:
        chunks = name.split('.')
        for end_i in xrange(len(chunks), 0, -1):
            config = local_registry.get('.'.join(chunks[:end_i]))
            if config:
                kwargs = _args_to_kwargs(config, skip=1)
                break

    # Fall back onto defaults for the server.
    if not kwargs:
        try:
            kwargs = _args_to_kwargs(local_registry[None], skip=1)
        except KeyError:
            raise ValueError('no default for %r Shotgun server' % server)

    # Augment it with the cache.
    if use_cache:
        cache_url = os.environ.get('SGCACHE')
        if cache_url:

            cache_url = cache_url.strip('/')
            if not cache_url.startswith('http'):
                cache_url = 'http://' + cache_url

            # Make sure it works.
            if _ping_sgcache(cache_url):
                server = cache_url

    kwargs['base_url'] = server

    # Augment it with environment variables.
    if use_envvars:
        for name, _ in _default_args:
            envvar_name = 'SHOTGUN_' + name.upper()
            if envvar_name in os.environ:
                kwargs[name] = os.environ[envvar_name]

    # Augment with extra kwargs to this function.
    for k, v in extra.iteritems():
        if k in _default_arg_names:
            kwargs[k] = v
        else:
            raise KeyError(k)

    if sys.flags.verbose:
        print '# %s.connect(...): %r -> %r' % (__package__, name, _kwargs_to_args(kwargs))

    return kwargs


# This is the older API that quite a few things use.
def get_args(name=None, server=None, auto_name_stack_depth=0, *args, **kwargs):
    return _kwargs_to_args(get_kwargs(name, server, auto_name_stack_depth + 1, *args, **kwargs))


def connect(name=None, server=None, *args, **kwargs):

    server = _conform_server(server)

    if server == 'mock':
        from sgmock import Shotgun
        sg = Shotgun()

        if 'SGMOCK_FIXTURE' in os.environ:
            fixture = os.environ['SGMOCK_FIXTURE']
            if ':' in fixture:
                module_name, func_name = fixture.split(':')
            else:
                module_name = 'sgmock.fixture.setup'
                func_name = fixture
            module = __import__(module_name, fromlist=['.'])
            func = getattr(module, func_name)
            func(sg)

        return sg

    kwargs = get_kwargs(name, server, *args, **kwargs)
    kwargs.setdefault('connect', False)

    return shotgun_api3.Shotgun(**kwargs)
