from flask_webapi import serializers
from unittest import TestCase


class TestFieldParameters(TestCase):
    """
    Tests for `required`, `allow_none`, `allow_blank`, `default`, `dump_to`, `load_from`
    """
    def test_required(self):
        """
        By default a field must be included in the input.
        """
        field = serializers.IntegerField(required=True)

        with self.assertRaises(serializers.ValidationError):
            field.safe_deserialize(serializers.missing)

    def test_not_required(self):
        """
        If `required=False` then a field may be omitted from the input.
        """
        field = serializers.IntegerField()
        self.assertEqual(field.safe_deserialize(serializers.missing), serializers.missing)

    def test_disallow_none(self):
        """
        By default `None` is not a valid input.
        """
        field = serializers.IntegerField()
        with self.assertRaises(serializers.ValidationError) as exc_info:
            field.safe_deserialize(None)
        self.assertEqual(exc_info.exception.message, ['This field may not be null.'])

        # blank value is converted to None if allow_blank=False
        field = serializers.StringField()
        with self.assertRaises(serializers.ValidationError) as exc_info:
            field.safe_deserialize('')
        self.assertEqual(exc_info.exception.message, ['This field may not be blank.'])

    def test_allow_none(self):
        """
        If `allow_none=True` then `None` is a valid input.
        """
        field = serializers.IntegerField(allow_none=True)
        output = field.safe_deserialize(None)
        self.assertEqual(output, None)

        # blank value is converted to None if allow_blank=False
        field = serializers.StringField(allow_none=True)
        output = field.safe_deserialize('')
        self.assertEqual(output, None)

    def test_disallow_blank(self):
        """
        By default '' is not a valid input.
        """
        field = serializers.StringField()
        with self.assertRaises(serializers.ValidationError) as exc_info:
            field.safe_deserialize('')
        self.assertEqual(exc_info.exception.message, ['This field may not be blank.'])

    def test_allow_blank(self):
        """
        If `allow_blank=True` then '' is a valid input.
        """
        field = serializers.StringField(allow_blank=True)
        output = field.safe_deserialize('')
        self.assertEqual(output, '')

    def test_default(self):
        """
        If `default` is set, then omitted values get the default input.
        """
        field = serializers.IntegerField(default=123)
        output = field.safe_deserialize(serializers.missing)
        self.assertEqual(output, 123)

    def test_dump_to(self):
        """
        If `dump_to` is set, then output field name get the dump_to value.
        """
        class Serializer(serializers.Serializer):
            field = serializers.StringField(dump_to='other')
        data = Serializer().load(data={'field': 'abc'})
        self.assertEqual(data, {'other': 'abc'})

    def test_load_from(self):
        """
        If `load_from` is set, then field value is get from load_from.
        """
        class Serializer(serializers.Serializer):
            field = serializers.StringField(load_from='other')
        data = Serializer().load(data={'other': 'abc'})
        self.assertEqual(data, {'field': 'abc'})

    def test_dump_only(self):
        """
        Dump-only fields should not be deserialized.
        """
        class Serializer(serializers.Serializer):
            field_1 = serializers.IntegerField(dump_only=True)
            field_2 = serializers.IntegerField()

        data = {'field_1': 123, 'field_2': 456}
        serializer = Serializer()

        self.assertEqual(serializer.load(data), {'field_2': 456})

    def test_load_only(self):
        """
        Load-only fields should not be serialized.
        """
        class Serializer(serializers.Serializer):
            field_1 = serializers.IntegerField(load_only=True)
            field_2 = serializers.IntegerField()

        data = {'field_1': 123, 'field_2': 456}
        serializer = Serializer()

        self.assertEqual(serializer.dump(data), {'field_2': 456})


class FieldValues(object):
    """
    Base class for testing valid and invalid input values.
    """

    def get_items(self, mapping_or_list_of_two_tuples):
        # Tests accept either lists of two tuples, or dictionaries.
        if isinstance(mapping_or_list_of_two_tuples, dict):
            # {value: expected}
            return mapping_or_list_of_two_tuples.items()
        # [(value, expected), ...]
        return mapping_or_list_of_two_tuples

    def test_valid_inputs(self):
        """
        Ensure that valid values return the expected validated data.
        """
        for input_value, expected_output in self.get_items(self.valid_inputs):
            self.assertEqual(self.field.safe_deserialize(input_value), expected_output)

    def test_invalid_inputs(self):
        """
        Ensure that invalid values raise the expected validation error.
        """
        for input_value, expected_failure in self.get_items(self.invalid_inputs):
            with self.assertRaises(serializers.ValidationError) as exc_info:
                self.field.safe_deserialize(input_value)
            self.assertEqual(exc_info.exception.message, expected_failure)

    def test_outputs(self):
        for output_value, expected_output in self.get_items(self.outputs):
            self.assertEqual(self.field.serialize(output_value), expected_output)


class TestIntegerField(FieldValues, TestCase):
    """
    Valid and invalid values for `IntegerField`.
    """
    valid_inputs = {
        '1': 1,
        '0': 0,
        1: 1,
        0: 0,
        1.0: 1,
        0.0: 0,
    }
    invalid_inputs = {
        'abc': ['A valid integer is required.'],
        '1.0': ['A valid integer is required.']
    }
    outputs = {
        '1': 1,
        '0': 0,
        1: 1,
        0: 0,
        1.0: 1,
        0.0: 0
    }
    field = serializers.IntegerField()


class TestMinMaxIntegerField(FieldValues, TestCase):
    """
    Valid and invalid values for `IntegerField` with min and max limits.
    """
    valid_inputs = {
        '1': 1,
        '3': 3,
        1: 1,
        3: 3,
    }
    invalid_inputs = {
        0: ['Must be at least 1.'],
        4: ['Must be at most 3.'],
        '0': ['Must be at least 1.'],
        '4': ['Must be at most 3.'],
    }
    outputs = {}
    field = serializers.IntegerField(min_value=1, max_value=3)


class TestStringField(FieldValues, TestCase):
    """
    Valid and invalid values for `StringField`.
    """
    valid_inputs = {
        1: '1',
        'abc': 'abc'
    }
    invalid_inputs = {
        '': ['This field may not be blank.']
    }
    outputs = {
        1: '1',
        'abc': 'abc'
    }
    field = serializers.StringField()

    def test_trim_whitespace_default(self):
        field = serializers.StringField()
        self.assertEqual(field.deserialize(' abc '), 'abc')

    def test_trim_whitespace_disabled(self):
        field = serializers.StringField(trim_whitespace=False)
        self.assertEqual(field.deserialize(' abc '), ' abc ')

    def test_disallow_blank_with_trim_whitespace(self):
        field = serializers.StringField(allow_blank=False, trim_whitespace=True)

        with self.assertRaises(serializers.ValidationError) as exc_info:
            field.safe_deserialize('   ')
        self.assertEqual(exc_info.exception.message, ['This field may not be blank.'])


class TestMinMaxStringField(FieldValues, TestCase):
    """
    Valid and invalid values for `StringField` with min and max limits.
    """
    valid_inputs = {
        12: '12',
        'ab': 'ab',
        'abcd': 'abcd',
    }
    invalid_inputs = {
        '1': ['Shorter than minimum length 2.'],
        1: ['Shorter than minimum length 2.'],
        'abcde': ['Longer than maximum length 4.'],
        12345: ['Longer than maximum length 4.'],
    }
    outputs = {}
    field = serializers.StringField(min_length=2, max_length=4)