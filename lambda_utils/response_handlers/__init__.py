import logging


class BaseResponseHandler:
    def on_execution(self, event):
        logging.debug(event)
        return event

    def on_exception(self, ex):
        logging.exception(str(ex))
        raise

    def on_response(self, response):
        logging.debug(response)
        return response
