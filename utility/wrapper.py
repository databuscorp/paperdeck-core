import datetime

import django
from dacite import from_dict

from utility.utilityobj import ListResponse, Pagination


class Wrapper:

    def to_data_class(self, data_class, instance):
        if isinstance(instance, django.db.models.query.QuerySet):
            data_arr = []
            for s_ins in instance:
                rdict = {}
                self.__dmodels_to_dict(s_ins, rdict)
                dclass = from_dict(data_class=data_class, data=rdict)
                data_arr.append(dclass)
            return data_arr
        else:
            rdict = {}
            self.__dmodels_to_dict(instance, rdict)
            dclass = from_dict(data_class=data_class, data=rdict)
            return dclass

    def __dmodels_to_dict(self, instance, rdict):
        opts = instance._meta
        fields = opts.fields
        for field in fields:
            if field.name == field.attname:
                fv = getattr(instance, field.name)
                if isinstance(fv, datetime.datetime):
                    rdict[field.name] = fv.isoformat()
                elif isinstance(fv, datetime.date):
                    rdict[field.name] = fv.strftime('%Y-%m-%d')
                else:
                    rdict[field.name] = fv
            else:
                related = getattr(instance, field.name)
                if related is not None:
                    rdict[field.name] = self.__dmodels_to_dict(related, {})
                else:
                    rdict[field.name] = None
        return rdict

    def to_list(self, data_arr, index, limit):
        has_previous = index > 1
        has_next = len(data_arr) > limit
        prev_index = index - 1 if has_previous else 1
        next_index = index + 1 if has_next else index
        page_obj = Pagination(
            index=index, limit=limit,
            has_previous=has_previous, has_next=has_next,
            next_index=next_index, prev_index=prev_index
        )
        if has_next:
            data_arr.pop()
        return ListResponse(data=data_arr, pagination=page_obj)
