import json

import pytest
from hamcrest import assert_that, equal_to
from mock import patch
from pytest import fixture

from lambda_utils import LambdaProcessor
from lambda_utils.response_handlers import cloudformation as module
from lambda_utils.response_handlers.cloudformation import Cloudformation, FAILED, logging, \
    send_signal


@fixture
def event():
    return {
        'StackId': 'stack_id',
        'ResponseURL': 'https://cloudformation-custom-resource-response-euwest1.s3-eu-west-1.amazonaws.com/stack_id',
        'RequestType': 'CREATE',
        'ServiceToken': "some_lambda_arn",
        'ResourceType': 'Custom::CustomResource',
        'PhysicalResourceId': 'stack_name-logical_resource_id',
        'RequestId': 'request_id',
        'LogicalResourceId': 'logical_resource_id',
        'ResourceProperties': {}
    }


@fixture
def sns_event(event):
    return {"Records": [{"Sns": {"Message": json.dumps(event)}}]}


class TestCloudformation:
    def test_on_execution_store_event(self, event):
        cloudformation = Cloudformation()

        result = cloudformation.on_execution(event)

        assert_that(result, equal_to(event))
        assert_that(cloudformation.event, equal_to(event))

    @patch.object(logging, 'exception')
    def test_on_exception_calls_logging_exception(self, exception_mock, event):
        exception = Exception()

        @LambdaProcessor(response_handler=Cloudformation())
        def function(event, context):
            raise exception

        with pytest.raises(Exception) as ex:
            function(event, None)

        exception_mock.assert_called_once_with(str(exception))

    @patch.object(module, 'send_signal')
    def test_on_exception_failed_signal_is_send(self, send_signal_mock, event):
        exception = Exception('some_exception')

        @LambdaProcessor(response_handler=Cloudformation())
        def function(event, context):
            raise exception

        function(event, None)

        send_signal_mock.assert_called_once_with(event, FAILED, "some_exception")

    @patch.object(module, 'Request')
    @patch.object(module, 'HTTPHandler')
    @patch.object(module, 'build_opener')
    def test_on_exception_failed_signal_is_send_from_sns_event(self, build_opener_mock, http_handler_mock, request_mock, event, sns_event):
        exception = Exception('some_exception')
        response_body = '{"Data": {}, "LogicalResourceId": "logical_resource_id", "PhysicalResourceId": "stack_name-logical_resource_id", "Reason": "some_exception", "RequestId": "request_id", "StackId": "stack_id", "Status": "FAILED"}'

        @LambdaProcessor(response_handler=Cloudformation())
        def function(event, context):
            raise exception

        function(sns_event, None)

        build_opener_mock.assert_called_once_with(http_handler_mock)
        request_mock.assert_called_once_with(event['ResponseURL'], data=response_body)
        build_opener_mock.return_value.open.assert_called_once_with(request_mock.return_value)


class TestSendSignal:
    @patch.object(module, 'build_opener')
    def test_send_signal(self, build_opener, event):
        send_signal(event, 'SUCCESS', 'some_random_string')

        build_opener.assert_called_once_with(module.HTTPHandler)
        build_opener.return_value.open.assert_called_once()

    @patch.object(module, 'build_opener')
    def test_send_signal_non_serializable_reason(self, build_opener, event):
        send_signal(event, 'SUCCESS', object())

        build_opener.assert_called_once_with(module.HTTPHandler)
        build_opener.return_value.open.assert_called_once()
