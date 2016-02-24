from flask_webapi.mimetypes import MimeType
from flask_webapi.utils import missing
from unittest import TestCase


class TestMimeType(TestCase):
    def test_full_type(self):
        mimetype = MimeType('application/json')

        self.assertEqual('application/json', mimetype.full_type)
        self.assertEqual('application', mimetype.main_type)
        self.assertEqual('json', mimetype.sub_type)
        self.assertEqual({}, mimetype.params)

    def test_empty_full_type(self):
        mimetype = MimeType('')

        self.assertEqual('', mimetype.full_type)
        self.assertEqual('', mimetype.main_type)
        self.assertEqual('', mimetype.sub_type)

    def test_invalid_full_type(self):
        mimetype = MimeType('application')

        self.assertEqual('application', mimetype.full_type)
        self.assertEqual('application', mimetype.main_type)
        self.assertEqual('', mimetype.sub_type)

    def test_with_parameters(self):
        mimetype = MimeType('application/json ; encoding = utf-8;indent=4')

        self.assertEqual('application/json', mimetype.full_type)
        self.assertEqual('application', mimetype.main_type)
        self.assertEqual('json', mimetype.sub_type)
        self.assertEqual('utf-8', mimetype.params['encoding'])
        self.assertEqual('4', mimetype.params['indent'])

    def test_empty_parameter(self):
        mimetype = MimeType('application/json;=utf-8;indent=')

        self.assertEqual(missing, mimetype.params.get('encoding', missing))
        self.assertEqual(missing, mimetype.params.get('indent', missing))

    def test_parameter_with_multiple_equals(self):
        mimetype = MimeType('application/json;indent=1=2')

        self.assertEqual(missing, mimetype.params.get('indent', missing))

    def test_match_with_params(self):
        mimetype = MimeType('application/json')
        mimetype2 = MimeType('application/json;encoding=utf-8')
        self.assertTrue(mimetype.match(mimetype2))
        self.assertTrue(mimetype2.match(mimetype))

    def test_match_with_different_main_types(self):
        mimetype = MimeType('application/json')
        mimetype2 = MimeType('otherthing/json')
        self.assertFalse(mimetype.match(mimetype2))
        self.assertFalse(mimetype2.match(mimetype))

    def test_match_with_different_sub_types(self):
        mimetype = MimeType('application/json')
        mimetype2 = MimeType('application/xml')
        self.assertFalse(mimetype.match(mimetype2))
        self.assertFalse(mimetype2.match(mimetype))

    def test_match_with_star(self):
        mimetype = MimeType('application/json')
        mimetype2 = MimeType('application/*')
        self.assertTrue(mimetype.match(mimetype2))
        self.assertTrue(mimetype2.match(mimetype))

        mimetype = MimeType('application/json')
        mimetype2 = MimeType('*/json')
        self.assertTrue(mimetype.match(mimetype2))
        self.assertTrue(mimetype2.match(mimetype))
