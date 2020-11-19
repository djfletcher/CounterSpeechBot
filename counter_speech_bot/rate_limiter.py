import datetime
import time


class RateLimiter:
	""" Basic rate limiter, nothing fancy """

	def __init__(self, max_calls_per_second, padding_microseconds=0):
		self.each_call_duration_seconds = 1 / max_calls_per_second
		self.last_call_time = datetime.datetime.fromtimestamp(0)
		self.padding_microseconds = padding_microseconds

	def wait(self):
		next_call_time = self.last_call_time + datetime.timedelta(seconds=self.each_call_duration_seconds)
		time.sleep(max(0, next_call_time.timestamp() - datetime.datetime.now().timestamp()))
		# If padding is needed, pretend that the last call was made n microseconds later than it actually was.
		# This is useful so that we are slightly below the rate limit and don't hit it
		self.last_call_time = datetime.datetime.now() + datetime.timedelta(microseconds=self.padding_microseconds)
