#!/usr/bin/env python
# encoding: utf-8
"""
api.py

Created by Jeremiah Shirk on 2011-10-01.
Copyright (c) 2011 Monitis. All rights reserved.
"""

import os
from hashlib import sha1
from hmac import new as new_hmac
from base64 import b64encode
from datetime import datetime
from time import time, mktime
from urllib import urlencode
from urllib2 import Request, urlopen, HTTPError
from json import loads
from copy import deepcopy


class MonitisError(Exception):

    '''Errors encountered during interaction with the Monitis API

    On encountering an error, the Monitis API web service will return either
    a JSON or XML encoded error response, or else a HTTP error response with
    the error message in the body of the page.  In the case that an HTTP error
    is returned, MonitisError will be raised, with the error in
    MonitisError.msg.
    '''

    msg = None

    def __init__(self, msg):
        Exception.__init__(self, msg)
        self.msg = msg

    def __str__(self):
        return 'MonitisError({0})'.format(self.msg)

# API operations on existing instances are methods
# Other API operations, new operations, and helpers are functions


def _api_url():
    if Monitis.sandbox is True:
        return Monitis.sandbox_url
    else:
        return Monitis.default_url

def camel2under(word):
    ''' Translate camelCase strings to underscore delimited compound words '''
    result_list = []
    for i in range(len(word)-1):
        result_list.append(word[i])
        if word[i].islower() and word[i+1].isupper():
            result_list.append('_')
    result_list.append(word[-1])
    return ''.join(result_list).lower()


def decode_json(json=None):
    '''Deserialize json to a python object.'''
    try:
        return loads(json)
    except ValueError, error:
        raise MonitisError(': '.join(['JSON parse error', str(error)]))


def validate_kwargs(required, optional, **kwargs):
    ''' Ensure required kwargs are present, and map to camelCase

    Arguments required and optional should each be a dict mapping from
    names in the SDK format to names in the API format.  If both are
    present, then take the value from the API format argument.

    Alternatively, required and optional can be lists of camelCase
    identifiers in the format used by the native API.  Then, identifiers
    in the SDK underscore_delimited format will also be accepted.

    Include any unexpected kwargs in the result
    '''
    # turn required list into dict
    temp_required = {}
    temp_optional = {}
    if isinstance(required, list):
        for word in required:
            temp_required[camel2under(word)] = word
        required = temp_required

    # turn optional list into dict
    if isinstance(optional, list):
        for word in optional:
            temp_optional[camel2under(word)] = word
        optional = temp_optional

    result_kwargs = {}
    for lc, cc in required.items():
        value =  kwargs.pop(lc, None)
        if value is None:
            value = kwargs.pop(cc, None)
        if value is None:
            raise MonitisError(lc + " is required")
        else:
            result_kwargs[cc] = value

    for lc, cc in optional.items():
        value =  kwargs.pop(lc, None)
        if value is None:
            value = kwargs.pop(cc, None)
        if value is not None:
            result_kwargs[cc] = value

    # include any kwargs not removed by pop, i.e. not in required or optional
    result_kwargs.update(kwargs)
    return result_kwargs


def resolve_apikey():
    '''Resolve the Monitis API key outside of a Monitis instance'''
    # check the class variable
    apikey = Monitis.apikey
    if apikey is not None:
        return apikey

    # get the value from the environment
    if Monitis.sandbox is True:
        apikey = environ_key('MONITIS_SANDBOX_APIKEY')
    else:
        apikey = environ_key('MONITIS_APIKEY')
    if apikey is not None:
        return apikey

    # if we got this far, the API key wasn't found
    raise MonitisError('The Monitis API key is required')


def resolve_secretkey():
    '''Resolve the Monitis secret key outside of a Monitis instance'''
    # check the class variable
    secretkey = Monitis.secretkey
    if secretkey is not None:
        return secretkey

    # get the value from the environment
    if Monitis.sandbox is True:
        secretkey = environ_key('MONITIS_SANDBOX_SECRETKEY')
    else:
        secretkey = environ_key('MONITIS_SECRETKEY')
    if secretkey is not None:
        return secretkey

    # if we got this far, the API key wasn't found
    raise MonitisError('The Monitis secret key is required')


def environ_key(name=None):
    """Helper method to get a key from os.environ

    Return value of environment variable name if it exists, None otherwise
    """
    try:
        return os.environ[name]
    except KeyError:
        return None


def timestamp():
    """Timestamp in the format required for Monitis API post requests

    Return a string containing current datetime in GMT
    with yyyy-MM-dd HH:mm:ss format
    """
    return datetime.utcnow().strftime("%F %T")


def checktime(dt=None):
    """Timestamp in the format required for monitor results

    dt - optional datetime

    Returns a string containing number of milliseconds
    since January 1, 1970, 00:00:00 GMT. If the optional argument
    dt is provided, then return the value as of the time as represented by
    that datetime object.  If no argument is provided, return the value as
    of now.
    """
    if dt is None:
        epoch_time = str(int(time()))
    else:
        epoch_time = str(int(mktime(dt.timetuple())))
    return epoch_time + "000"


# TODO remove redundant checksum call in Monitis class
def checksum(**kwargs):
    """Base64-encoded HMAC signature of the parameters string

    The checksum is caclulated as documented at:
        http://monitis.com/api/api.html#checkSum
    """

    # remove secretkey from kwargs, lookup if missing
    secretkey = kwargs.pop('secretkey', resolve_secretkey())

    # sort the args, and concatenate them
    param_string = ''.join([''.join([str(x), str(y)])
                            for x, y in sorted(kwargs.items())])

    return b64encode(str(new_hmac(secretkey, param_string, sha1).digest()))


def get(apikey=None, action=None, version='2', _url=None, **kwargs):
    """GET requests to the Monitis API

    Returns Python objects based on the JSON-encoded responses

    If _raw=True is passed in, then the raw HTTP Response will be returned
    """

    url = _url or _api_url()
    _raw = kwargs.pop('_raw', False) # remove _raw kwarg, default to False

    output = 'JSON'  # don't allow XML, so we can parse JSON response
    apikey = apikey or resolve_apikey()

    # sanity checks
    if not apikey:
        raise MonitisError("get: apikey is required")
    if not action:
        raise MonitisError("get: action is required")

    # build the request
    req_params = [('apikey', apikey), ('action', action),
                  ('output', output), ('version', version)]
    req_params.extend(kwargs.items())
    req_url = url + '?' + urlencode(req_params)

    # make the request
    if Monitis.debug:
        print "Request URL: " + req_url
    req = Request(req_url)
    try:
        res = urlopen(req)
    except HTTPError, error:
        raise MonitisError('API Error: ' + error.read())
    if _raw:
        return res
    res_json = res.read()
    if Monitis.debug:
        print "Response: " + res_json

    # build a python object out of the result
    return decode_json(res_json)


def post(apikey=None, secretkey=None, action=None, version=2,
         _url=None, **kwargs):
    ''' Non-OO POST to Monitis API

    Pass in POST args as kwargs
    If _raw=True is passed in, then the raw HTTP Response will be returned
    '''

    apikey = apikey or resolve_apikey()
    secretkey = secretkey or resolve_secretkey()
    url = _url or _api_url()
    output = 'JSON'

    _raw = kwargs.pop('_raw', False) # remove _raw kwarg, default to False

    if not action:
        raise MonitisError("post: action is required")

    post_args = deepcopy(kwargs)
    post_args['apikey'] = apikey
    post_args['action'] = action
    post_args['version'] = version
    post_args['timestamp'] = timestamp()

    # calculate a checksum based on the values and secret key
    post_checksum = checksum(secretkey=secretkey, **post_args)

    # use urllib to post the values
    post_args['checksum'] = post_checksum
    post_params = urlencode(post_args)

    try:
        if Monitis.debug is True:
            print "Request URL: " + url
            print "Request params: " + str(post_args)
        result = urlopen(url, post_params)
    except HTTPError, error:
        raise MonitisError('API Error: ' + error.read())
    if _raw:
        return result
    ret = result.read()
    if Monitis.debug is True:
        print "Response: " + ret
    result.close()
    return decode_json(ret)


class Monitis:

    '''Encapsulate the Monitis API

    Encapsulate the Monitis RESTFUL API, to be subclassed by specific
    components of the API.

    '''

    debug = False
    sandbox = False
    apikey = None
    secretkey = None
    default_url = 'http://monitis.com/api'
    sandbox_url = 'http://sandbox.monitis.com/api'

    def resolve_apikey(self):
        """Resolve the Monitis API Key from the invoking shell

        Find the API Key

        First, check for a key local to this instance of Monitis.
        If not found in the instance, then check the class.  Finally,
        check the environment variable.  If no key is found in any of these
        places, then raise an exception.

        """
        # check the instance variable
        apikey = self.apikey
        if apikey is not None:
            return apikey

        # check the class variable and environment
        apikey = resolve_apikey()
        if apikey is not None:
            return apikey

        # if we got this far, the API key wasn't found
        raise MonitisError('The Monitis API key is required')

    def resolve_secretkey(self):
        """Resolve the Monitis Secret Key from the invoking shell

        Find the secret key

        First, check for a key local to this instance of Monitis.
        If not found in the instance, then check the class.  Finally,
        check the environment variable.  If no key is found in any of these
        places, then raise an exception.

        """
        # check the instance variable
        secretkey = self.secretkey
        if secretkey is not None:
            return secretkey

        # check the class variable
        secretkey = resolve_secretkey()
        if secretkey is not None:
            return secretkey

        # if we got this far, the secret key wasn't found
        raise MonitisError('The Monitis secret key is required')

    def __init__(self, apikey=None, secretkey=None, _url=None,
                 version=None, validation=None):
        '''Create a new Monitis object'''
        self.auth_token = None
        self.url = _url or _api_url()
        self.apikey = apikey or self.resolve_apikey()
        self.secretkey = secretkey or self.resolve_secretkey()
        self.validation = validation or 'HMACSHA1'
        self.version = version or '2'

    def post(self, **kwargs):
        """Post the dict in post_args to the Monitis REST API"""
        post_args = deepcopy(kwargs)
        post_args['apikey'] = self.apikey
        post_args['version'] = self.version
        post_args['timestamp'] = timestamp()

        # calculate a checksum based on the values and secret key
        post_checksum = self.checksum(**post_args)

        # use urllib to post the values
        post_args['checksum'] = post_checksum

        params = urlencode(post_args)
        try:
            if Monitis.debug is True:
                print "Request URL: " + self.url
                print "Request params: " + str(post_args)
            result = urlopen(self.url, params)
        except HTTPError, error:
            raise MonitisError('API Error: ' + error.read())
        ret = result.read()
        if Monitis.debug is True:
            print "Response: " + ret
        result.close()
        return ret

    def checksum(self, **kwargs):
        """Base64-encoded HMAC signature of the parameters string

        The checksum is caclulated as documented at:

            http://monitis.com/api/api.html#checkSum

            - sort all request parameters alphabetically by param name
            - join param-value pairs in a string: param1value1param2value2...
            - return Base64-encoded RFC 2104-compliant HMAC signature of the
              constructed string using your secrect key
        """
        try:
            # if a secretkey is in **kwargs, use it, and remove it
            secretkey = kwargs['secretkey']
            del kwargs['secretkey']
        except KeyError:
            # if the kwargs lookup fails, get secretkey elsewhere
            secretkey = self.secretkey or resolve_secretkey()
        args = kwargs.items()
        args.sort()

        param_string = ''
        for key, value in args:
            param_string += str(key)
            param_string += str(value)
        return b64encode(str(new_hmac(secretkey, param_string, sha1).digest()))
