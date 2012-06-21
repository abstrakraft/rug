class Writer(object):
	def write():
		raise NotImplementedError('Writer.write is an abstract function')

class StringWriter(Writer):
	def __init__(self):
		super(StringWriter, self).__init__()
		self.string = ''

	def write(self, str):
		if str:
			if str[-1] != '\n':
				str += '\n'
			self.string += str

class FileWriter(Writer):
	def __init__(self, file):
		super(FileWriter, self).__init__()
		self.file = file

	def write(self, str):
		if str:
			if str[-1] != '\n':
				str += '\n'
			self.file.write(str)

class OutputBuffer(object):
	def __init__(self, arg=None, prefix=''):
		if isinstance(arg, OutputBuffer):
			self._prefix = arg.get_prefix() + prefix
		else:
			self._prefix = prefix
		
	def get_prefix(self):
		return self._prefix

	def append(self, str):
		raise NotImplementedError('OutputBuffer.append is an abstract function')

	def spawn(self, prefix=''):
		return type(self)(self, prefix)

class WriterOutputBuffer(OutputBuffer):
	def __init__(self, arg, prefix=''):
		super(WriterOutputBuffer, self).__init__(arg, prefix)
		if isinstance(arg, WriterOutputBuffer):
			self._writer = arg.get_writer()
		else:
			self._writer = arg

	def get_writer(self):
		return self._writer

	def append(self, str):
		if str:
			self._writer.write(self._prefix + str)

class NullOutputBuffer(OutputBuffer):
	def append(self, str):
		pass
