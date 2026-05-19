from typing import TypeVar

O = TypeVar('O')
M = TypeVar('M')


class ThreadLocal:
    __scope = None
    __user_id = None
    __scope_dict = None

    def __init__(self, scope_dict):
        if scope_dict is not None:
            self.__scope = scope_dict.get('scope', 'default')
            self.__user_id = scope_dict.get('user_id')
            self.__scope_dict = scope_dict

    def _scope(self):
        return self.__scope

    def _user_id(self):
        return self.__user_id

    def _scope_dict(self):
        return self.__scope_dict
