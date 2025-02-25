import os

import yaml

CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../config.yml'))

def load_config():
    with open(CONFIG_PATH, 'r') as file:
        config = yaml.safe_load(file)
    return config

def get(key):
    config = load_config()
    return config[key]
