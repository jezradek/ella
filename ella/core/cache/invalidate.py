try:
    import cPickle as pickle
except ImportError:
    import pickle

import stomp
from django.dispatch import dispatcher
from django.db.models import signals
from django.conf import settings

import logging
log = logging.getLogger('cache')
AMQ_DESTINATION = '/topic/ella'


class CacheDeleter(object):
    def __init__(self):
        self.signal_handler = self
        self.conn = None

    def on_error(self, header, message):
        " Log AMQ/stomp error message "
        log.error('AMQ: %s' % header)

    def on_disconnected(self):
        log.error('AMQ: Connection was lost!')

    def _send(self, msg, type, key=None, model=None):
        " Send message to AMQ "
        if self.conn:
            headers = {'Type': type, 'Key': key, 'Model': model}
            self.conn.send(msg, headers=headers, destination=AMQ_DESTINATION)

    def register_test(self, model, test, key):
        self._send(test, 'test', key, model)

    def register_pk(self, instance, key):
        msg = pickle.dumps(instance)
        self._send(msg, 'pk', key)

    def register_dependency(self, src_key, obj_key):
        self._send('', 'dep', src_key, obj_key)

    def propagate_signal(self, sender, instance):
        """
        Trap the pre_save and pre_delete signal and
        invalidate the relative cache entries.
        """
        # log about received signal
        log.debug('Signal from "%s" received.' % sender)
        try:
            # propagate the signal to Cache Invalidator
            self._send(pickle.dumps(instance), 'del')
        except:
            log.error('Can not send message to AMQ.')

    def connect(self, *args, **kwargs):

        # initialize connection to ActiveMQ
        self.conn = stomp.Connection(*args, **kwargs)
        self.conn.start()
        self.conn.connect()

    def disconnect(self):
        self.conn.stop()

CACHE_DELETER = CacheDeleter()
ACTIVE_MQ_HOST = getattr(settings, 'ACTIVE_MQ_HOST', None)
ACTIVE_MQ_PORT = getattr(settings, 'ACTIVE_MQ_PORT', 61613)


if ACTIVE_MQ_HOST:
    try:
        CACHE_DELETER.connect([(ACTIVE_MQ_HOST, ACTIVE_MQ_PORT)])

        # start listening for any model
        # register the proper propagation function for intercepting the proper signals
        dispatcher.connect(CACHE_DELETER.propagate_signal, signal=signals.pre_save)
        dispatcher.connect(CACHE_DELETER.propagate_signal, signal=signals.post_save)
        dispatcher.connect(CACHE_DELETER.propagate_signal, signal=signals.post_delete)
        log.debug('Start listening for any model')
    except:
        log.warning('ActiveMQ not running')
