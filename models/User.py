"""User classes"""
import hashlib
from . import Base


class User(Base.Object):
    """User class"""

    def __init__(self):
        super(self.__class__, self).__init__()
        self.username = ''
        self.password = ''
        self.guardian_id = ''
        self.roles = {}
        self.positions = []

    @staticmethod
    def hash_password(password):
        """Hashes the password"""
        hashed_password = hashlib.sha256(password).hexdigest()
        return hashed_password

    def get_validator(self):
        return Validator(self)

    @staticmethod
    def get_factory():
        return Factory()


class Validator(Base.Validator):
    """User validator"""

    def get_field_requirements(self):
        return {
            'uuid': Base.FIELD_REQUIRED,
            'username': Base.FIELD_REQUIRED,
            'password': Base.FIELD_REQUIRED,
            'roles': Base.FIELD_OPTIONAL,
            'positions': Base.FIELD_OPTIONAL,
            'guardians': Base.FIELD_OPTIONAL,
        }


class Factory(Base.Factory):
    """User Factory"""

    @staticmethod
    def load_by_session(session_id):
        """Load the user based on the session UUID"""
        # TO-DO: implement this
        return session_id

    @staticmethod
    def get_uuid_prefix():
        return 'usr'

    @staticmethod
    def _get_object_class():
        return User

    @staticmethod
    def _get_persister():
        return Persister()


class Persister(Base.Persister):

    """Persists User objects"""

    @staticmethod
    def _get_table_name():
        return 'Users'
