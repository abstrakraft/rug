class Buffer(object):
	def __init__(self):
		self._buffer = ""

	def get_buffer(self):
		return self._buffer[:-1]

	def clear(self):
		self._buffer = ""

	def append(self, str):
		if str:
			if str[-1] != '\n':
				self._buffer += str + '\n'
			else:
				self._buffer += str

class NullBuffer(object):
	def get_buffer(self):
		pass

	def clear(self):
		pass

	def append(self, str):
		pass
