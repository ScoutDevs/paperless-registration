"""Base classes"""

import boto3
import shortuuid

from . import InvalidObjectException
from . import MultipleMatchException
from . import RecordNotFoundException

FIELD_REQUIRED = 'required'
FIELD_OPTIONAL = 'optional'


class Object(object):
    """Base class"""

    def __init__(self):
        pass

    def get_validator(self):  # pylint: disable=no-self-use
        """
        Returns a Validator object for validation

        Must be defined by the child class.
        """
        raise Exception('SYSTEM ERROR: validator not defined.')

    def validate(self):
        """Validate the object"""
        return self.get_validator().validate()

    def set_from_data(self, data):
        """Update object from dict"""
        for key, _ in self.__dict__.items():
            if key in data:
                setattr(self, key, data[key])

    def to_dict(self):
        """Convert object to dict"""
        data = {}
        for key, val in self.__dict__.items():
            if key[0] != '_':
                data[key] = val
            else:
                data[key[1:]] = val
        return data

    def fields(self):
        """Return list of object properties"""
        fields = []
        for key, _ in self.__dict__.items():
            if key[0] == '_':
                fields.append(key[1:])
            else:
                fields.append(key)
        return fields

    def get_uuid(self):
        """Generates a UUID"""
        return "{}-{}".format(self.get_uuid_prefix(), shortuuid.uuid())

    @staticmethod
    def get_uuid_prefix():
        """Must be implemented by child"""
        raise Exception('Invalid implementation.')


class Validator(object):
    """Validates data construct"""

    def __init__(self, obj):
        self.obj = obj

    def get_field_requirements(self):  # pylint: disable=no-self-use
        """
        Specify which fields are used, and whether they're required

        Must be defined by the child class.
        """
        raise Exception('SYSTEM ERROR: field requirements not defined.')

    def _validate_required_fields(self):
        """Validate that the data provided includes all required fields"""
        valid = True
        errors = []

        for key, value in self.get_field_requirements().items():
            if value == FIELD_REQUIRED:
                if key not in self.obj.to_dict() or not self.obj.to_dict()[key]:
                    errors.append('Missing required field "{}"'.format(key))
                    valid = False

        return (valid, errors)

    def prepare_for_validate(self):
        """
        Called by the persister prior to validation & storage

        Useful for setting derived values.
        """
        pass

    def _validate(self):  # pylint: disable=no-self-use
        """Any additional validation can be done in this method in the child"""
        return (True, [])

    def valid(self):
        """Determine validity of the object"""
        self.prepare_for_validate()
        (requirements_valid, _) = self._validate_required_fields()
        (other_valid, _) = self._validate()
        return requirements_valid and other_valid

    def validate(self):
        """Validates the object"""
        errors = self.get_validation_errors()
        if errors:
            raise InvalidObjectException(errors[0])

    def get_validation_errors(self):
        """Provide errors associated with validation"""
        self.prepare_for_validate()
        (_, requirements_errors) = self._validate_required_fields()
        (_, other_errors) = self._validate()
        return requirements_errors + other_errors


class Factory(object):
    """Base Factory"""

    def __init__(self):
        self.__persister = None

    def load_by_uuid(self, uuid):
        """Load by UUID"""
        return self.load_from_database({'uuid': uuid})

    @classmethod
    def get_uuid_prefix(cls):
        """Get UUID prefix"""
        return cls._get_object_class().get_uuid_prefix()

    def load_from_database(self, search_data):
        """Load from DB by primary key"""
        item_data = self._persister.get(search_data)
        return self.construct(item_data)

    def load_from_database_query(self, search_data):
        """Load from DB by secondary key"""
        items = self._persister.query(search_data)
        if len(items) == 0:
            raise RecordNotFoundException('Record not found')
        elif len(items) > 1:
            raise MultipleMatchException('Multiple matches found')
        return self.construct(items[0])

    def construct(self, data, invalid_field_exceptions=True):
        """Create object from dict"""
        klass = self._get_object_class()  # pylint: disable=assignment-from-no-return
        obj = klass()

        for key, _ in data.items():
            if key in obj.fields():
                try:
                    setattr(obj, key, data[key])
                except AttributeError:
                    pass
            else:
                if invalid_field_exceptions:
                    raise Exception('Unknown "{}" field "{}"'.format(klass.__name__, key))
        return obj

    @property
    def _persister(self):
        if not self.__persister:
            self.__persister = self.get_persister()  # pylint: disable=assignment-from-no-return
        return self.__persister

    @staticmethod
    def get_persister():
        """Get persister object"""
        raise Exception('SYSTEM ERROR: persister not defined.')

    @staticmethod
    def _get_object_class():
        """Get object class"""
        raise Exception('SYSTEM ERROR: class not defined.')


class Persister(object):
    """Persists objects"""

    def __init__(self):
        dynamodb = boto3.resource('dynamodb')
        self.table = dynamodb.Table(self._get_table_name())

    def save(self, obj):
        """Save to DB"""
        obj.get_validator().validate()
        persist_obj = self.__class__.get_persistable_object(obj)
        self.table.put_item(Item=persist_obj)

    @staticmethod
    def get_persistable_object(obj):
        """
        Give DynamoDB what it wants

        DynamoDB wants a dict, not an object
        DynamoDB won't store empty fields, so get rid of 'em
        """
        new_dict = {}
        for key, val in obj.to_dict().items():
            if val != '':
                new_dict[key] = val
        return new_dict

    def get(self, key):
        """Load from DB by primary key"""
        item = self.table.get_item(Key=key)
        if 'Item' in item:
            return item['Item']
        else:
            raise RecordNotFoundException('Record not found')

    def query(self, search_data):
        """Search DB with index and return 0 or more records"""
        expression = None
        if '__index__' in search_data:
            index_name = search_data['__index__']
            del search_data['__index__']
        for key, value in search_data.items():
            if not index_name:
                index_name = key
            if expression:
                expression = expression & boto3.dynamodb.conditions.Key(key).eq(value)
            else:
                expression = boto3.dynamodb.conditions.Key(key).eq(value)  # pylint: disable=redefined-variable-type
        result = self.table.query(
            IndexName=index_name,
            KeyConditionExpression=expression
        )

        if 'Items' in result:
            items = result['Items']
        else:
            raise Exception('Error searching')

        return items

    def delete(self, obj):
        """Delete from DB"""
        self.table.delete_item(Key={'uuid': obj.uuid})

    @staticmethod
    def _get_table_name():
        """Must be implemented by child class."""
        raise Exception('SYSTEM ERROR: No table name specified.')
