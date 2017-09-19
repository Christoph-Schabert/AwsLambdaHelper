import logging
from time import sleep

import pytest
from hamcrest import assert_that, equal_to
from mock import MagicMock, patch
from pytest import fixture

from lambda_utils import BaseResponseHandler, LambdaProcessor
from tests.conftest import Context


@fixture
def event():
    return {"Some": "Event"}


@fixture
def response():
    return {"Some": "Response"}


@fixture
def exception():
    return Exception('SomeException')


class TestWrappedFunction:
    @patch.object(LambdaProcessor, 'on_execution')
    def test_calls_on_execution(self, on_execution_mock, event):
        @LambdaProcessor()
        def function(event, context):
            pass

        function(event, None)

        on_execution_mock.assert_called_once_with(event)

    @patch.object(LambdaProcessor, 'on_response', return_value='some_response')
    def test_calls_on_response(self, on_response_mock, response):
        @LambdaProcessor()
        def function(event, context):
            return response

        result = function(None, None)

        assert_that(result, equal_to(on_response_mock.return_value))
        on_response_mock.assert_called_once_with(response)

    @patch.object(LambdaProcessor, 'on_exception', return_value='SomeExceptionResponse')
    def test_calls_on_exception_on_timeout(self, on_exception_mock):
        @LambdaProcessor()
        def function(event, context):
            sleep(0.7)

        result = function(None, Context(600))

        assert_that(result, equal_to(on_exception_mock.return_value))
        on_exception_mock.assert_called_once()

    @patch.object(LambdaProcessor, 'on_exception', return_value='SomeExceptionResponse')
    def test_calls_on_exception_on_exception(self, on_exception_mock):
        @LambdaProcessor()
        def function(event, context):
            raise Exception('SomeException')

        result = function(None, None)

        assert_that(result, equal_to(on_exception_mock.return_value))
        on_exception_mock.assert_called_once()


class TestOnFunctions:
    def test_on_init_triggers_loggers(self):
        loggers = [MagicMock(), MagicMock()]
        function = lambda event, context: event

        LambdaProcessor(loggers=loggers).on_init(function)

        for logger in loggers:
            logger.on_init.assert_called_once_with(function)

    def test_on_execution_triggers_loggers(self, event):
        loggers = [MagicMock(), MagicMock()]

        LambdaProcessor(loggers=loggers).on_execution(event)

        for logger in loggers:
            logger.on_execution.assert_called_once_with(event)

    def test_on_execution_triggers_response_handler(self, event):
        response_handler = MagicMock()

        LambdaProcessor(response_handler=response_handler).on_execution(event)

        response_handler.on_execution_assert_called_once_with(event)

    @patch.object(logging, 'debug')
    def test_on_execution_logging_event(self, debug_mock, event):
        LambdaProcessor().on_execution(event)

        debug_mock.assert_called_once_with(event)

    def test_on_response_returns_value(self, response):
        result = LambdaProcessor().on_response(response)

        assert_that(result, equal_to(result))

    @patch.object(logging, 'debug')
    def test_on_response_logging_response(self, debug_mock, response):
        LambdaProcessor().on_response(response)

        debug_mock.assert_called_once_with(response)

    @patch.object(logging, 'exception')
    def test_on_exception_logging_exception(self, exception_mock):
        exception = Exception('some_exception')

        @LambdaProcessor()
        def function(event, context):
            raise exception

        with pytest.raises(Exception) as ex:
            function(None, None)

        assert_that(ex.value, equal_to(exception))
        exception_mock.assert_called_once_with(str(exception))

    @patch.object(BaseResponseHandler, 'on_exception')
    def test_on_exception_forward_exception(self, on_exception_mock, exception):
        @LambdaProcessor()
        def function(event, context):
            raise exception

        result = function(None, None)

        assert_that(result, equal_to(on_exception_mock.return_value))
        on_exception_mock.assert_called_once_with(exception)


class TestSecondsUntilTimeout:
    def test_returns_seconds(self):
        context = MagicMock()
        context.get_remaining_time_in_millis.return_value = 5000

        result = LambdaProcessor().seconds_until_timeout(context)

        assert_that(result, equal_to(4.0))
