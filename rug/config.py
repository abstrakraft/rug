import string

class ConfigFile(object):
	#section_header = re.compile('\[(?P<section>[^]]*)\]')
	#kv_pair = re.compile('(?P<key>[^=]*)\s*=\s*(?P<value>.*)')

	def __init__(self, conf):
		self._conf = conf

	def sections(self):
		return self._conf.keys()

	def get(self, section, key=None):
		if section not in self._conf:
			if (section is None) and (key is None):
				return {}
			else:
				raise KeyError('No section %s in configuration' % section)

		if key is None:
			return self._conf[section]
		else:
			if key not in self._conf[section]:
				raise KeyError('no key %s in configuration section %s' % (key, section))
			else:
				return self._conf[section][key]

	def set(self, section, key, value):
		if section not in self._conf:
			self._conf[section] = {}
		self._conf[section][key] = value

	@classmethod
	def from_file(cls, file):
		conf = {}
		current_section = None
		for line in file:
			line = string.strip(line)
			#blank
			if len(line) == 0:
				continue
			#section header
			elif (line[0] == '[') and (line[-1] == ']'):
				current_section = line[1:-1].strip()
				conf[current_section] = {}
			else:
				split = line.find('=')
				#kv_pair
				if split != -1:
					key = line[:split].strip()
					value = line[split+1:].strip()
				if current_section not in conf:
					conf[current_section] = {}
				conf[current_section][key] = value

		return cls(conf)

	@classmethod
	def from_path(cls, path):
		return cls.from_file(open(path))

	def to_file(self, file):
		if None in self._conf:
			for (k,v) in self._conf[None].items():
				file.write('%s = %s\n' % (k,v))

		for (section, kv) in self._conf.items():
			if section is None: continue

			file.write('[%s]\n' % section)
			for (k,v) in kv.items():
				file.write('%s = %s\n' % (k,v))

			file.write('\n')

	def to_path(self, path):
		self.to_file(open(path, 'w'))
