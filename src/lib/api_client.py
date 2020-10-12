from lib import websock

#------------------------------------------------------------------------------

_Debug = True

#------------------------------------------------------------------------------

def run(method, kwargs={}, cb=None, ):
    if _Debug:
        print('api_client.run %r cb=%r' % (method, cb, ))
    jd = {'command': 'api_call', 'method': method, 'kwargs': kwargs, }
    return websock.ws_call(json_data=jd, cb=cb)

#------------------------------------------------------------------------------

def process_health(cb=None):
    return run('process_health', cb=cb)


def identity_get(cb=None):
    return run('identity_get', cb=cb)


def network_connected(wait_timeout=0, cb=None):
    return run('network_connected', kwargs={'wait_timeout': wait_timeout, }, cb=cb)


def user_observe(nickname, attempts=5, cb=None):
    return run('user_observe', kwargs={'nickname': nickname, 'attempts': 5, }, cb=cb)


def friends_list(cb=None):
    return run('friends_list', cb=cb)


def friend_add(global_user_id, alias='', cb=None):
    return run('friend_add', kwargs={'trusted_user_id': global_user_id, 'alias': alias, }, cb=cb)


def friend_remove(global_user_id, cb=None):
    return run('friend_remove', kwargs={'user_id': global_user_id, }, cb=cb)


def message_history(recipient_id=None, sender_id=None, message_type=None, offset=0, limit=100, cb=None):
    return run('message_history', kwargs={
        'recipient_id': recipient_id,
        'sender_id': sender_id,
        'message_type': message_type,
        'offset': offset,
        'limit': limit,
    }, cb=cb)


def message_send(recipient_id, data, ping_timeout=30, message_ack_timeout=15, cb=None):
    return run('message_send', kwargs={
        'recipient_id': recipient_id,
        'data': data,
        'ping_timeout': ping_timeout,
        'message_ack_timeout': message_ack_timeout,
    }, cb=cb)