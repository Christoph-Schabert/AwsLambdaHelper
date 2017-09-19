# -*- coding: utf-8 -*-
__author__ = """CloudHeads"""
__email__ = 'theguys@cloudheads.io'
__version__ = '0.2.10'

from concurrent.futures import ThreadPoolExecutor

from logger import BaseLogger
from response_handlers import BaseResponseHandler


class LambdaProcessor:
    def __init__(self, response_handler=None, loggers=None):

        self.response_handler = response_handler or BaseResponseHandler()
        self.loggers = loggers or [BaseLogger()]

    def on_init(self, function):
        for logger in self.loggers:
            logger.on_init(function)

    def on_execution(self, event):
        for logger in self.loggers:
            logger.on_execution(event)
        return self.response_handler.on_execution(event)

    def on_response(self, response):
        return self.response_handler.on_response(response)

    def on_exception(self, ex):
        return self.response_handler.on_exception(ex)

    def __call__(self, function):
        self.on_init(function)
        self.function = function
        return self.wrapped_function

    def seconds_until_timeout(self, context):
        if hasattr(context, 'get_remaining_time_in_millis'):
            seconds = (context.get_remaining_time_in_millis() / 1000.00) - 1.0
            return seconds

    def wrapped_function(self, event, context):
        try:
            event = self.on_execution(event)
            timer = ThreadPoolExecutor(max_workers=1).submit(self.function, event, context)
            response = timer.result(timeout=self.seconds_until_timeout(context))
            return self.on_response(response)
        except Exception as ex:
            return self.on_exception(ex)
