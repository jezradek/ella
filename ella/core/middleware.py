try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local

from django import template
from django.core.cache import cache
from django.utils.cache import get_cache_key, learn_cache_key, patch_response_headers, get_max_age
from django.conf import settings

ECACHE_INFO = 'ella.core.middleware.ECACHE_INFO'

_thread_locals = local()
def get_current_request():
    return getattr(_thread_locals, 'request', None)

class ThreadLocalsMiddleware(object):
    """Middleware that gets various objects from the
    request object and saves them in thread local storage."""

    def process_request(self, request):
        _thread_locals.request = request

class DoubleRenderMiddleware(object):
    def process_response(self, request, response):
        if response.status_code != 200 or not getattr(settings, 'DOUBLE_RENDER', False):
            return response

        c = template.RequestContext(request, {'SECOND_RENDER': True})
        t = template.Template(response.content)
        response.content = t.render(c)
        return response

class CacheMiddleware(object):
    """
    Cache middleware. If this is enabled, each Django-powered page will be
    cached (based on URLs).

    Only parameter-less GET or HEAD-requests with status code 200 are cached.

    The number of seconds each page is stored for is set by the
    "max-age" section of the response's "Cache-Control" header, falling back to
    the CACHE_MIDDLEWARE_SECONDS setting if the section was not found.

    If CACHE_MIDDLEWARE_ANONYMOUS_ONLY is set to True, only anonymous requests
    (i.e., those not made by a logged-in user) will be cached. This is a
    simple and effective way of avoiding the caching of the Django admin (and
    any other user-specific content).

    This middleware expects that a HEAD request is answered with a response
    exactly like the corresponding GET request.

    When a hit occurs, a shallow copy of the original response object is
    returned from process_request.

    Pages will be cached based on the contents of the request headers
    listed in the response's "Vary" header. This means that pages shouldn't
    change their "Vary" header.

    This middleware also sets ETag, Last-Modified, Expires and Cache-Control
    headers on the response object.
    """
    def __init__(self, cache_timeout=None, key_prefix=None, cache_anonymous_only=None):
        self.cache_timeout = cache_timeout
        if cache_timeout is None:
            self.cache_timeout = settings.CACHE_MIDDLEWARE_SECONDS
        self.key_prefix = key_prefix
        if key_prefix is None:
            self.key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
        if cache_anonymous_only is None:
            self.cache_anonymous_only = getattr(settings, 'CACHE_MIDDLEWARE_ANONYMOUS_ONLY', False)
        else:
            self.cache_anonymous_only = cache_anonymous_only

    def process_request(self, request):
        "Checks whether the page is already cached and returns the cached version if available."
        if self.cache_anonymous_only:
            assert hasattr(request, 'user'), "The Django cache middleware with CACHE_MIDDLEWARE_ANONYMOUS_ONLY=True requires authentication middleware to be installed. Edit your MIDDLEWARE_CLASSES setting to insert 'django.contrib.auth.middleware.AuthenticationMiddleware' before the CacheMiddleware."

        if not request.method in ('GET', 'HEAD') or request.GET:
            request._cache_update_cache = False
            return None # Don't bother checking the cache.

        if self.cache_anonymous_only and request.user.is_authenticated():
            request._cache_update_cache = False
            return None # Don't cache requests from authenticated users.

        cache_key = get_cache_key(request, self.key_prefix)
        if cache_key is None:
            request._cache_update_cache = True
            return None # No cache information available, need to rebuild.

        response = cache.get(cache_key, None)
        if response is None:
            request._cache_update_cache = True
            return None # No cache information available, need to rebuild.

        request._cache_update_cache = False
        return response

    def process_response(self, request, response):
        "Sets the cache, if needed."
        if not hasattr(request, '_cache_update_cache') or not request._cache_update_cache:
            # We don't need to update the cache, just return.
            return response
        if request.method != 'GET':
            # This is a stronger requirement than above. It is needed
            # because of interactions between this middleware and the
            # HTTPMiddleware, which throws the body of a HEAD-request
            # away before this middleware gets a chance to cache it.
            return response
        if not response.status_code == 200:
            return response
        # Try to get the timeout from the "max-age" section of the "Cache-
        # Control" header before reverting to using the default cache_timeout
        # length.
        timeout = get_max_age(response)
        if timeout == None:
            timeout = self.cache_timeout
        elif timeout == 0:
            # max-age was set to 0, don't bother caching.
            return response
        patch_response_headers(response, timeout)
        cache_key = learn_cache_key(request, response, timeout, self.key_prefix)
        cache.set(cache_key, response, timeout)
        return response
