from typing import TypeVar

from utility.uthread import ThreadLocal
from utility.wrapper import Wrapper

O = TypeVar('O')
M = TypeVar('M')


class DBService(ThreadLocal):
    def __init__(self, scope):
        super().__init__(scope)

    def post(self, obj: O, model: M):
        data = {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
        if getattr(obj, 'id', None) is None:
            data.pop('id', None)
            data_obj = model.objects.create(**data)
            return data_obj.id
        else:
            model.objects.filter(id=obj.id).update(**data)
            return obj.id

    def get_all(self, obj: O, model: M):
        data_arr = model.objects.all()
        wrapper_obj = Wrapper()
        return wrapper_obj.to_data_class(obj, data_arr)

    def filter_all(self, obj: O, model: M, **kwargs):
        data_arr = model.objects.filter(**kwargs)
        wrapper_obj = Wrapper()
        return wrapper_obj.to_data_class(obj, data_arr)

    def get_one(self, obj: O, model: M, **kwargs):
        try:
            data = model.objects.get(**kwargs)
        except model.DoesNotExist:
            return None
        wrapper_obj = Wrapper()
        return wrapper_obj.to_data_class(obj, data)
