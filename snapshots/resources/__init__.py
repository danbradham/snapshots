import os


path = os.path.dirname(__file__)


def get(resource):
    return os.path.join(path, resource).replace('\\', '/')
