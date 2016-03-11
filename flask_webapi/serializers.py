import datetime
import decimal
import uuid

from collections import OrderedDict
from .exceptions import ValidationError
from .utils import dateparse, html, missing, timezone
from .utils.caching import cached_property
from .validators import MaxValueValidator, MinValueValidator, MaxLengthValidator, MinLengthValidator


MISSING_ERROR_MESSAGE = (
    'ValidationError raised by `{class_name}`, but error key `{key}` does '
    'not exist in the `error_messages` dictionary.'
)


class Field(object):
    default_error_messages = {
        'required': 'This field is required.',
        'null': 'This field may not be null.',
        'validator_failed': 'Invalid value.'
    }

    def __init__(self, dump_only=False, load_only=False, required=None, default=missing, allow_none=None,
                 dump_to=None, load_from=None, error_messages=None, validators=None):
        self.dump_only = dump_only
        self.load_only = load_only
        self.default = default
        self.allow_none = allow_none
        self.dump_to = dump_to
        self.load_from = load_from
        self.validators = validators or []

        # If `required` is unset, then use `True` unless a default is provided.
        if required is None:
            self.required = default is missing
        else:
            self.required = required

        if allow_none is None:
            self.allow_none = default is None
        else:
            self.allow_none = allow_none

        # Collect default error message from self and parent classes
        messages = {}
        for cls in reversed(self.__class__.__mro__):
            messages.update(getattr(cls, 'default_error_messages', {}))
        messages.update(error_messages or {})
        self.error_messages = messages

        self.field_name = None
        self.parent = None

    @cached_property
    def root(self):
        """
        Returns the top-level serializer for this field.
        """
        root = self
        while root.parent is not None:
            root = root.parent
        return root

    def bind(self, field_name, parent):
        self.field_name = field_name
        self.parent = parent

        if not self.dump_to:
            self.dump_to = field_name

        if not self.load_from:
            self.load_from = field_name

    def get_attribute(self, instance):
        if isinstance(instance, dict):
            value = instance.get(self.field_name, missing)
        else:
            value = getattr(instance, self.field_name, missing)

        if value is missing:
            return self.get_default()

        return value

    def get_value(self, dictionary):
        value = dictionary.get(self.load_from, missing)

        if not html.is_html_input(dictionary):
            return value

        if value != '':
            return value

        if self.allow_none:
            return None

        return missing

    def get_default(self):
        if callable(self.default):
            return self.default()
        return self.default

    def serialize(self, value):
        raise NotImplementedError()

    def deserialize(self, data):
        raise NotImplementedError()

    def safe_deserialize(self, data):
        if data is missing:
            if getattr(self.root, 'partial', False):
                return missing

            if self.required:
                self._fail('required')

            return self.get_default()

        if data is None:
            if not self.allow_none:
                self._fail('null')
            return None

        validated_data = self.deserialize(data)
        self._validate(validated_data)
        return validated_data

    def _fail(self, key, **kwargs):
        try:
            msg = self.error_messages[key]
            message_string = msg.format(**kwargs)
            raise ValidationError(message_string)
        except KeyError:
            class_name = self.__class__.__name__
            msg = MISSING_ERROR_MESSAGE.format(class_name=class_name, key=key)
            raise AssertionError(msg)

    def _validate(self, data):
        errors = []
        for validator in self.validators:
            try:
                if validator(data) is False:
                    self._fail('validator_failed')
            except ValidationError as err:
                if isinstance(err.message, dict):
                    errors.append(err.message)
                else:
                    errors.extend(err.message)
        if errors:
            raise ValidationError(errors)


class BooleanField(Field):
    default_error_messages = {
        'invalid': '"{input}" is not a valid boolean.'
    }

    TRUE_VALUES = {'t', 'T', 'true', 'True', 'TRUE', '1', 1, True}
    FALSE_VALUES = {'f', 'F', 'false', 'False', 'FALSE', '0', 0, 0.0, False}

    def deserialize(self, data):
        try:
            if data in self.TRUE_VALUES:
                return True
            if data in self.FALSE_VALUES:
                return False
        except TypeError:
            pass
        self._fail('invalid', input=data)

    def serialize(self, value):
        if value is None:
            return None
        if value in self.TRUE_VALUES:
            return True
        if value in self.FALSE_VALUES:
            return False
        return bool(value)


class DateField(Field):
    default_error_messages = {
        'invalid': 'Date has wrong format.',
        'datetime': 'Expected a date but got a datetime.',
    }

    def deserialize(self, data):
        if isinstance(data, datetime.datetime):
            self._fail('datetime')

        if isinstance(data, datetime.date):
            return data

        try:
            parsed = dateparse.parse_date(data)
            if parsed is not None:
                return parsed
        except (ValueError, TypeError):
            pass

        self._fail('invalid')

    def serialize(self, value):
        if value is None:
            return None

        return value.isoformat()


class DateTimeField(Field):
    default_error_messages = {
        'invalid': 'Datetime has wrong format.',
        'date': 'Expected a datetime but got a date.',
    }

    default_timezone = None

    def __init__(self, default_timezone=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if default_timezone is not None:
            self.default_timezone = default_timezone

    def deserialize(self, data):
        if isinstance(data, datetime.datetime):
            return self._enforce_timezone(data)

        if isinstance(data, datetime.date):
            self._fail('date')

        try:
            parsed = dateparse.parse_datetime(data)
            if parsed is not None:
                return self._enforce_timezone(parsed)
        except (ValueError, TypeError):
            pass

        self._fail('invalid')

    def serialize(self, value):
        if value is None:
            return None

        value = value.isoformat()
        if value.endswith('+00:00'):
            value = value[:-6] + 'Z'
        return value

    def _enforce_timezone(self, value):
        """
        When `self.default_timezone` is `None`, always return naive datetimes.
        When `self.default_timezone` is not `None`, always return aware datetimes.
        """
        if self.default_timezone is not None and not timezone.is_aware(value):
            return timezone.make_aware(value, self.default_timezone)
        return value


class DecimalField(Field):
    default_error_messages = {
        'invalid': 'A valid number is required.',
        'max_value': 'Ensure this value is less than or equal to {max_value}.',
        'min_value': 'Ensure this value is greater than or equal to {min_value}.',
        'max_digits': 'Ensure that there are no more than {max_digits} digits in total.',
        'max_decimal_places': 'Ensure that there are no more than {max_decimal_places} decimal places.',
        'max_whole_digits': 'Ensure that there are no more than {max_whole_digits} digits before the decimal point.',
        'max_string_length': 'String value too large.'
    }
    MAX_STRING_LENGTH = 1000  # Guard against malicious string inputs.

    def __init__(self, max_digits, decimal_places, max_value=None, min_value=None, **kwargs):
        super(DecimalField, self).__init__(**kwargs)

        self.max_digits = max_digits
        self.decimal_places = decimal_places

        self.max_value = max_value
        self.min_value = min_value

        if self.max_digits is not None and self.decimal_places is not None:
            self.max_whole_digits = self.max_digits - self.decimal_places
        else:
            self.max_whole_digits = None

        if self.max_value is not None:
            message = self.error_messages['max_value'].format(max_value=self.max_value)
            self.validators.append(MaxValueValidator(self.max_value, message=message))
        if self.min_value is not None:
            message = self.error_messages['min_value'].format(min_value=self.min_value)
            self.validators.append(MinValueValidator(self.min_value, message=message))

    def deserialize(self, data):
        """
        Validate that the input is a decimal number and return a Decimal
        instance.
        """
        data = str(data)
        if len(data) > self.MAX_STRING_LENGTH:
            self._fail('max_string_length')

        try:
            value = decimal.Decimal(data)

            # Check for NaN and for infinity and negative infinity.
            if value.is_nan() or value.is_infinite():
                self._fail('invalid')

            return self._validate_precision(value)
        except decimal.DecimalException:
            self._fail('invalid')

    def serialize(self, value):
        if not isinstance(value, decimal.Decimal):
            value = decimal.Decimal(str(value))

        quantized = self._quantize(value)

        return '{0:f}'.format(quantized)

    def _quantize(self, value):
        """
        Quantize the decimal value to the configured precision.
        """
        context = decimal.getcontext().copy()
        context.prec = self.max_digits
        return value.quantize(
            decimal.Decimal('.1') ** self.decimal_places,
            context=context)

    def _validate_precision(self, value):
        """
        Ensure that there are no more than max_digits in the number, and no
        more than decimal_places digits after the decimal point.
        Override this method to disable the precision validation for input
        values or to enhance it in any way you need to.
        """
        sign, digittuple, exponent = value.as_tuple()

        if exponent >= 0:
            # 1234500.0
            total_digits = len(digittuple) + exponent
            whole_digits = total_digits
            decimal_places = 0
        elif len(digittuple) > abs(exponent):
            # 123.45
            total_digits = len(digittuple)
            whole_digits = total_digits - abs(exponent)
            decimal_places = abs(exponent)
        else:
            # 0.001234
            total_digits = abs(exponent)
            whole_digits = 0
            decimal_places = total_digits

        if self.max_digits is not None and total_digits > self.max_digits:
            self._fail('max_digits', max_digits=self.max_digits)
        if self.decimal_places is not None and decimal_places > self.decimal_places:
            self._fail('max_decimal_places', max_decimal_places=self.decimal_places)
        if self.max_whole_digits is not None and whole_digits > self.max_whole_digits:
            self._fail('max_whole_digits', max_whole_digits=self.max_whole_digits)

        return value


class DictField(Field):
    default_error_messages = {
        'not_a_dict': 'Expected a dictionary of items but got type "{input_type}".'
    }

    def __init__(self, child, *args, **kwargs):
        super(DictField, self).__init__(*args, **kwargs)
        self.child = child() if isinstance(child, type) else child

    def deserialize(self, data):
        """
        Dicts of native values <- Dicts of primitive datatypes.
        """
        if not isinstance(data, dict):
            self._fail('not_a_dict', input_type=type(data).__name__)

        return {
            str(key): self.child.safe_deserialize(value) for key, value in data.items()
        }

    def serialize(self, value):
        """
        List of object instances -> List of dicts of primitive datatypes.
        """
        return {
            str(key): self.child.serialize(val) for key, val in value.items()
        }


class IntegerField(Field):
    default_error_messages = {
        'invalid': 'A valid integer is required.',
        'max_value': 'Must be at most {max_value}.',
        'min_value': 'Must be at least {min_value}.',
        'max_string_length': 'String value too large.'
    }

    MAX_STRING_LENGTH = 1000  # Guard against malicious string inputs.

    def __init__(self, min_value=None, max_value=None, **kwargs):
        super().__init__(**kwargs)
        self.min_value = min_value
        self.max_value = max_value

        if self.min_value is not None:
            message = self.error_messages['min_value'].format(min_value=self.min_value)
            self.validators.append(MinValueValidator(self.min_value, message=message))

        if self.max_value is not None:
            message = self.error_messages['max_value'].format(max_value=self.max_value)
            self.validators.append(MaxValueValidator(self.max_value, message=message))

    def deserialize(self, value):
        if isinstance(value, str) and len(value) > self.MAX_STRING_LENGTH:
            self._fail('max_string_length')

        try:
            return int(value)
        except (ValueError, TypeError):
            self._fail('invalid')

    def serialize(self, value):
        if value is None:
            return None
        return int(value)


class FloatField(Field):
    default_error_messages = {
        'invalid': 'A valid number is required.',
        'max_value': 'Ensure this value is less than or equal to {max_value}.',
        'min_value': 'Ensure this value is greater than or equal to {min_value}.',
        'max_string_length': 'String value too large.'
    }

    MAX_STRING_LENGTH = 1000  # Guard against malicious string inputs.

    def __init__(self, min_value=None, max_value=None, **kwargs):
        super().__init__(**kwargs)
        self.min_value = min_value
        self.max_value = max_value

        if self.max_value is not None:
            message = self.error_messages['max_value'].format(max_value=self.max_value)
            self.validators.append(MaxValueValidator(self.max_value, message=message))

        if self.min_value is not None:
            message = self.error_messages['min_value'].format(min_value=self.min_value)
            self.validators.append(MinValueValidator(self.min_value, message=message))

    def deserialize(self, data):
        if isinstance(data, str) and len(data) > self.MAX_STRING_LENGTH:
            self._fail('max_string_length')

        try:
            return float(data)
        except (TypeError, ValueError):
            self._fail('invalid')

    def serialize(self, value):
        if value is None:
            return None
        return float(value)


class ListField(Field):
    default_error_messages = {
        'not_a_list': 'Expected a list of items but got type "{input_type}".',
        'empty': 'This list may not be empty.'
    }

    def __init__(self, child, allow_empty=True, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.child = child() if isinstance(child, type) else child
        self.allow_empty = allow_empty

    def get_value(self, dictionary):
        value = dictionary.get(self.load_from, missing)

        if value == missing:
            return value

        if html.is_html_input(dictionary):
            value = dictionary.getlist(self.load_from)

        return value

    def deserialize(self, data):
        """
        List of dicts of native values <- List of dicts of primitive datatypes.
        """
        if not isinstance(data, list):
            self._fail('not_a_list', input_type=type(data).__name__)

        if not self.allow_empty and len(data) == 0:
            self._fail('empty')

        return [self.child.safe_deserialize(item) for item in data]

    def serialize(self, data):
        """
        List of object instances -> List of dicts of primitive datatypes.
        """
        return [self.child.serialize(item) for item in data]


class StringField(Field):
    default_error_messages = {
        'blank': 'This field may not be blank.',
        'max_length': 'Longer than maximum length {max_length}.',
        'min_length': 'Shorter than minimum length {min_length}.'
    }

    def __init__(self, allow_blank=False, trim_whitespace=True, min_length=None, max_length=None, **kwargs):
        super().__init__(**kwargs)
        self.allow_blank = allow_blank
        self.trim_whitespace = trim_whitespace
        self.min_length = min_length
        self.max_length = max_length

        if self.min_length is not None:
            message = self.error_messages['min_length'].format(min_length=self.min_length)
            self.validators.append(MinLengthValidator(self.min_length, message=message))

        if self.max_length is not None:
            message = self.error_messages['max_length'].format(max_length=self.max_length)
            self.validators.append(MaxLengthValidator(self.max_length, message=message))

    def get_value(self, dictionary):
        value = dictionary.get(self.load_from, missing)

        if not html.is_html_input(dictionary):
            return value

        if value != '':
            return value

        if self.allow_blank:
            return ''

        if self.allow_none:
            return None

        return missing

    def deserialize(self, data):
        value = str(data)

        if self.trim_whitespace:
            value = value.strip()

        if value == '' and not self.allow_blank:
            if self.allow_none:
                return None
            self._fail('blank')

        return value

    def serialize(self, value):
        if value is None:
            return None
        return str(value)


class UUIDField(Field):
    default_error_messages = {
        'invalid': '"{value}" is not a valid UUID.',
    }

    def deserialize(self, data):
        if isinstance(data, uuid.UUID):
            return data

        try:
            return uuid.UUID(hex=data)
        except (AttributeError, ValueError):
            self._fail('invalid', value=data)

    def serialize(self, value):
        return str(value)


class SerializerMetaclass(type):
    def __new__(mcs, name, bases, attrs):
        attrs['_declared_fields'] = mcs._get_declared_fields(bases, attrs)
        return super(SerializerMetaclass, mcs).__new__(mcs, name, bases, attrs)

    @classmethod
    def _get_declared_fields(mcs, bases, attrs):
        fields = []

        for attr_name, attr in list(attrs.items()):
            if isinstance(attr, type) and issubclass(attr, Field):
                attr = attr()
            if isinstance(attr, Field):
                fields.append((attr_name, attr))

        for base in reversed(bases):
            if hasattr(base, '_declared_fields'):
                fields = list(base._declared_fields.items()) + fields

        return OrderedDict(fields)


class Serializer(Field, metaclass=SerializerMetaclass):
    default_error_messages = {
        'invalid': 'Invalid data. Expected a dictionary, but got {datatype}.'
    }

    def __init__(self, only=None, many=False, partial=False, envelope=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.only = only or ()
        self.many = many
        self.partial = partial
        self.envelope = envelope

    @cached_property
    def fields(self):
        """
        A dictionary of {field_name: field_instance}.
        """
        # `fields` is evaluated lazily. We do this to ensure that we don't
        # have issues importing modules that use ModelSerializers as fields,
        # even if Django's app-loading stage has not yet run.
        ret = {}
        for field_name, field in self._declared_fields.items():
            field.bind(field_name, self)
            ret[field_name] = field
        return ret

    @cached_property
    def load_fields(self):
        lst = []

        for field in self.fields.values():
            if self.only and field.field_name not in self.only:
                continue

            if field.dump_only:
                continue

            lst.append(field)

        return lst

    @cached_property
    def dump_fields(self):
        lst = []

        for field in self.fields.values():
            if self.only and field.field_name not in self.only:
                continue

            if field.load_only:
                continue

            lst.append(field)

        return lst

    def load(self, data):
        if self.many:
            return [self.safe_deserialize(value) for value in data]

        return self.safe_deserialize(data)

    def dump(self, instance):
        if self.many:
            data = [self.serialize(value) for value in instance]
        else:
            data = self.serialize(instance)

        if self.envelope:
            data = {self.envelope: data}

        return data

    def deserialize(self, data):
        if not isinstance(data, dict):
            message = self.error_messages['invalid'].format(datatype=type(data).__name__)
            raise ValidationError(message)

        result = dict()
        errors = OrderedDict()

        for field in self.load_fields:
            try:
                value = field.get_value(data)
                value = field.safe_deserialize(value)
                if value is not missing:
                    result[field.field_name] = value
            except ValidationError as err:
                errors[field.field_name] = err.message

        if errors:
            raise ValidationError(errors, has_fields=True)

        return result

    def serialize(self, instance):
        result = dict()

        for field in self.dump_fields:
            value = field.get_attribute(instance)

            if value is not missing:
                result[field.dump_to] = field.serialize(value)

        return result
