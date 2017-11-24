import asyncio
import functools
import threading
import typing
from abc import abstractmethod


class Handler():
    def __init__(self, strategy) -> None:
        super().__init__()
        self.strategy = strategy

    @abstractmethod
    def handle(self, *args, **kwargs):
        pass


class AsyncHandler(Handler):
    def __init__(self, strategy: callable, *, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__(strategy)
        self.loop = loop

    def handle(self, *args, **kwargs):
        self._async_handle(loop=self.loop)

    def _async_handle(self, *, loop: typing.Optional[asyncio.AbstractEventLoop]):
        """
        The _async_handle
        :param args:
        :param kwargs:
        :return:
        """
        if loop is None:
            raise AsyncHandlerException("You need to pass a loop instance to the AsyncHandler")

        # if not loop.is_running():
        #           raise AsyncHandlerException("The loop instance passed to the AsyncHandler needs to be running")

        loop.call_soon(callback=functools.partial(self.strategy))


class AsyncHandlerException(BaseException):
    pass


class MessageLoopException(BaseException):
    pass


class MessageLoop(threading.Thread):
    """
    The message loop is a high level component that handles asynchronous messages on a separate thread.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop, debug: bool = False) -> None:
        """
        :param loop: The loop that handles incoming messages
        :param debug: The loop that handles the messages
        """
        super().__init__()
        self._loop = loop
        self._loop.set_debug(debug)
        self._pre_callback_listeners = {}
        self._post_callback_listeners = {}

    def run(self):
        """
        This is the callback run after calling start
        :return:
        """
        self._assert_has_loop()
        self._loop.run_forever()

    def shutdown(self, timeout=10):
        """
        Shuts down the thread and frees all held resources like the loop.
        Stops the loop as well.
        :param timeout:
        :return:
        """
        if self._loop is not None and self._loop.is_running():
            self._loop.stop()

        self._loop = None

        try:
            self.join(timeout=timeout)
        except RuntimeError:
            self._stop()

    def handle_message(self, handler: callable, *args, pre_notify=None, post_notify=None):
        self._assert_has_loop()
        if pre_notify is not None and pre_notify in self._pre_callback_listeners:
            callback = self._pre_callback_listeners[pre_notify]
            callback(self)

        if post_notify is not None and post_notify in self._post_callback_listeners:
            callback = self._post_callback_listeners[post_notify]
            self._loop.call_soon_threadsafe(callback=functools.partial(handler, *args, self, callback))
            return

        self._loop.call_soon_threadsafe(callback=functools.partial(handler, *args))

    def register_pre_callback_listener(self, handler: callable):
        self._pre_callback_listeners[id(handler)] = handler
        return functools.partial(self.handle_message, pre_notify=key)

    def register_post_callback_listener(self, handler: callable):
        key = id(handler)
        self._post_callback_listeners[key] = handler
        return functools.partial(self.handle_message, post_notify=key)

    def unregister_pre_callback_listener(self, handler: callable):
        del self._pre_callback_listeners[id(handler)]

    def unregister_post_callback_listener(self, handler: callable):
        del self._post_callback_listeners[id(handler)]

    def _assert_has_loop(self):
        if self._loop is None:
            raise MessageLoopException("You need to pass a loop instance to the MessageLoop!")

    def _assert_loop_is_running(self):
        if not self._loop.is_running():
            raise MessageLoopException("You need to run a loop instance prior to sending messages!")


event_loop = asyncio.new_event_loop()
loop = event_loop
message_loop = MessageLoop(loop=loop)


# handler, *args, self, callback
def my_callback(*args):
    print("was geht")


def handler_with_callback(a, b, message_loop=None, callback=None):
    callback()


handle_messages = message_loop.register_post_callback_listener(my_callback)

message_loop.start()

handle_messages(handler_with_callback, "paff", "paff")
message_loop.shutdown()
