import json
import pika
import traceback
from typing import Union


class Logger:

    def __init__(self, index, url, queue, to_elk=True):
        self.logger_name: str = index
        self.url = url
        self.queue = queue
        self.__connection: Union[pika.adapters.blocking_connection.BlockingConnection, None] = None
        self.__channel: Union[pika.adapters.blocking_connection.BlockingChannel, None] = None
        self.to_elk = to_elk

    def __get_connection(self):
        return pika.BlockingConnection(pika.connection.URLParameters(self.url))

    def __connect(self):
        # noinspection PyBroadException
        try:
            self.__connection = self.__get_connection()
            self.__channel = self.__connection.channel()

            try:
                self.__channel.queue_declare(self.queue, durable=True, auto_delete=False)
            except:
                # queue already exists, but it probably has some specific arguments. We need to reconnect
                self.__connection = self.__get_connection()
                self.__channel = self.__connection.channel()
        except:
            traceback.print_exc()
            try:
                self.__channel.close()
            except:
                pass

            try:
                self.__connection.close()
            except:
                pass
            self.__channel = None

    def log(self, context, stdout=False):
        if stdout:
            print(json.dumps(context), flush=True)

        if self.to_elk:
            if not self.__connection:
                self.__connect()

            context["index"] = self.logger_name

            # noinspection PyBroadException
            try:
                self.__channel.basic_publish("", self.queue, json.dumps(context))
            except:
                print(traceback.format_exc())
                self.__connection = None
