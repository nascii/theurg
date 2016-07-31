import os
import sys
import logging.config

import pytoml as toml

_BASE_PATH = os.path.dirname(os.path.dirname(__file__))
_CONFIG_PATH = os.path.join(_BASE_PATH, 'config.toml')

with open(_CONFIG_PATH, 'rb') as cfg:
    content = toml.load(cfg)

REQUIRED = {}

def get(*jpath, default=REQUIRED):
    value = content

    for part in jpath:
        try:
            value = value[part]
        except:
            if default is not REQUIRED:
                return default
            raise

    return value

def get_path(*args, **kwargs):
    value = get(*args, **kwargs)
    return os.path.normpath(os.path.join(_BASE_PATH, value))

# Logging.
logging.config.dictConfig(get('logging'))
