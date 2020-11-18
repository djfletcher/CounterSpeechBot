import datetime
import time


class RateLimiter:

	def __init__(self, max_calls_per_second):
		self.each_call_duration_seconds = 1 / max_calls_per_second
		# self.max_calls_per_second = max_calls_per_second
		self.last_call_time = datetime.datetime.fromtimestamp(0)

	def wait(self):
		next_call_time = self.last_call_time + datetime.timedelta(seconds=self.each_call_duration_seconds)
		time.sleep(max(0, next_call_time.timestamp() - datetime.datetime.now().timestamp()))
		self.last_call_time = datetime.datetime.now()
