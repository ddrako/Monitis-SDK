#!/usr/bin/env python
# encoding: utf-8
"""
agent.py

Created by Jeremiah Shirk on 2012-09-02.
Copyright (c) 2012 Monitis. All rights reserved.
"""

from monitis.api import get, post, MonitisError, validate_kwargs


def agents(**kwargs):
    ''' Get a user's agents '''
    required = []
    optional = ['keyRegExp']
    req_args = validate_kwargs(required, optional, **kwargs)
    return get(action='agents', **req_args)


def agent_info(**kwargs):
    ''' Get information regarding the specified agent '''
    required = ['agentId']
    optional = ['loadTests']
    req_args = validate_kwargs(required, optional, **kwargs)
    return get(action='agentInfo', **req_args)


def all_agents_snapshot(**kwargs):
    ''' Get last results for user's internal monitors '''
    required = ['platform']
    optional = ['timezone', 'tag']
    req_args = validate_kwargs(required, optional, **kwargs)
    return get(action='allAgentsSnapshot', **req_args)


def agent_snapshot(**kwargs):
    ''' Get last results for all monitors of the specified agent '''
    required = ['agentKey']
    optional = ['timezone']
    req_args = validate_kwargs(required, optional, **kwargs)
    return get(action='agentSnapshot', **req_args)


def delete_agents(**kwargs):
    ''' Delete agent from user's account '''
    required = []
    optional = ['agentIds', 'keyRegExp']
    req_args = validate_kwargs(required, optional, **kwargs)
    if not ('agentIds' in req_args or 'keyRegExp' in req_args):
        raise MonitisError('agent_ids or key_reg_exp is required')
    return post(action='deleteAgents', **req_args)


def download_agent(**kwargs):
    ''' Download the agent

    Returns a raw HTTP Response object instead of parsed JSON
    '''
    required = ['platform']
    optional = []
    req_args = validate_kwargs(required, optional, **kwargs)
    return post(action='downloadAgent', _raw=True, **req_args)
