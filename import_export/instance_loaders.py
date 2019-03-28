from django.core.exceptions import ValidationError
from django.utils.encoding import force_text

class BaseInstanceLoader:
    """
    Base abstract implementation of instance loader.
    """

    def __init__(self, resource, dataset=None):
        self.resource = resource
        self.dataset = dataset

    def get_instance(self, row):
        raise NotImplementedError


class ModelInstanceLoader(BaseInstanceLoader):
    """
    Instance loader for Django model.

    Lookup for model instance by ``import_id_fields``.
    """

    def get_queryset(self):
        return self.resource.get_queryset()

    def get_instance(self, row):
        errors = {}
        try:
            params = {}
            for key in self.resource.get_import_id_fields():
                field = self.resource.fields[key]
                try:
                    params[field.attribute] = field.clean(row)
                except ValueError as e:
                    errors[field.attribute] = ValidationError(
                        force_text(e), code="invalid")
            if errors:
                raise ValidationError(errors)
            if params:
                return self.get_queryset().get(**params)
            else:
                return None
        except self.resource._meta.model.DoesNotExist:
            return None


class CachedInstanceLoader(ModelInstanceLoader):
    """
    Loads all possible model instances in dataset avoid hitting database for
    every ``get_instance`` call.

    This instance loader work only when there is one ``import_id_fields``
    field.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        pk_field_name = self.resource.get_import_id_fields()[0]
        self.pk_field = self.resource.fields[pk_field_name]

        ids = [self.pk_field.clean(row) for row in self.dataset.dict]
        qs = self.get_queryset().filter(**{
            "%s__in" % self.pk_field.attribute: ids
            })

        self.all_instances = {
            self.pk_field.get_value(instance): instance
            for instance in qs
        }

    def get_instance(self, row):
        return self.all_instances.get(self.pk_field.clean(row))
