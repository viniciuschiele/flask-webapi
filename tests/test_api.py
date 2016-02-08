from flask import Flask
from flask_webapi import WebAPI, ViewBase, route
from unittest import TestCase


class TestWebAPI(TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.client = self.app.test_client()

    def test_add_view_after_init_app(self):
        self.api = WebAPI()
        self.api.init_app(self.app)
        self.api.add_view(View)

        response = self.client.post('/view/action')
        self.assertEqual(response.status_code, 204)

    def test_add_view_before_init_app(self):
        self.api = WebAPI()
        self.api.add_view(View)
        self.api.init_app(self.app)

        response = self.client.post('/view/action')
        self.assertEqual(response.status_code, 204)


class View(ViewBase):
    @route('/view/action', methods=['POST'])
    def get(self):
        pass