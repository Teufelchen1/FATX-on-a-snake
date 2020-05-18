import unittest, struct
from fatx.blocks import SuperBlock, FAT, DirectoryEntry, DirectoryEntryList, EntryType


class TestSuperBlock(unittest.TestCase):
	def setUp(self):
		self.f = open('tests/superblock.img', 'r+b')
		self.bytes = self.f.read(4096)

	def tearDown(self):
		self.f.close()

	def test_read_correct_superblock(self):
		sb = SuperBlock(self.bytes)
		self.assertEqual("FATX", sb.name)
		self.assertEqual("FATX", str(sb))
		self.assertEqual(1, sb.fatcopies)
		self.assertEqual(32, sb.clusternum)

	def test_read_incorrect_signuture(self):
		l = list(self.bytes)
		l[1] = ord('B')
		self.bytes = bytes(l)
		with self.assertRaises(AssertionError):
			SuperBlock(self.bytes)

	def test_read_invalid_signuture(self):
		l = list(self.bytes)
		l[1] = 0xFF
		self.bytes = bytes(l)
		with self.assertRaises(BaseException):
			SuperBlock(self.bytes)

	def test_too_long_superblock(self):
		self.bytes += b'\xFF\xFF'
		with self.assertRaises(BaseException):
			SuperBlock(self.bytes)

	def test_clusterSize(self):
		sb = SuperBlock(self.bytes)
		# Default Xbox cluster size is 16k
		self.assertEqual(16384, sb.clusterSize())


class TestFAT(unittest.TestCase):
	def setUp(self):
		self.f = open('tests/fat.img', 'r+b')
		self.bytes = self.f.read(65536)
		self.fat = FAT(self.bytes, 2)

	def tearDown(self):
		self.f.close()

	def test_numberClusters(self):
		self.assertEqual(32768, self.fat.numberClusters())
		self.assertEqual("32768 Clusters in map", str(self.fat

			))

	def test_getEntryType(self):
		self.assertEqual(EntryType.FATX_CLUSTER_AVAILABLE, self.fat.getEntryType(0x0000))
		self.assertEqual(EntryType.FATX_CLUSTER_END, self.fat.getEntryType(0xFFFF))
		self.assertEqual(EntryType.FATX_CLUSTER_END, self.fat.getEntryType(0xFFF8))
		self.assertEqual(EntryType.FATX_CLUSTER_DATA, self.fat.getEntryType(0x1111))

	def test_setEntryType(self):
		self.fat.setEntryType(0, EntryType.FATX_CLUSTER_AVAILABLE)
		self.assertEqual(EntryType.FATX_CLUSTER_AVAILABLE, self.fat.getEntryType(self.fat.clustermap[0]))
		self.fat.setEntryType(0, EntryType.FATX_CLUSTER_END)
		self.assertEqual(EntryType.FATX_CLUSTER_END, self.fat.getEntryType(self.fat.clustermap[0]))
		# Only available blocks can be used for data storage
		with self.assertRaises(AssertionError):
			self.fat.setEntryType(0x1111, 0)
		self.fat.setEntryType(0, EntryType.FATX_CLUSTER_AVAILABLE)
		self.fat.setEntryType(0, 0x1111)
		self.assertEqual(EntryType.FATX_CLUSTER_DATA, self.fat.getEntryType(self.fat.clustermap[0]))

	def test_clusterChain(self):
		chain = self.fat.clusterChain(0x0004)
		self.assertEqual(340, len(chain))
		for i in range(340):
			self.assertEqual(i+0x0004, chain[i])

	def test_clusterChain_wrong_start(self):
		with self.assertRaises(ValueError):
			self.fat.clusterChain(32767)

	def test_clusterChain_invalid_chain(self):
		self.fat.clustermap[5] = 0x0000
		with self.assertRaises(ValueError):
			self.fat.clusterChain(0x0004)

	def test_freeClusterChain(self):
		chain = self.fat.clusterChain(0x0004)
		self.fat.freeClusterChain(chain)
		for i in range(340):
			self.assertEqual(0x0000, self.fat.clustermap[i+0x0004])
		self.assertNotEqual(0x0000, self.fat.clustermap[0x0004+340+1])

	# ToDo: Test for a request that does not fit inside the FAT
	def test_getFreeClusterChain(self):
		test_chain = [10205, 10206, 10207, 10208, 10209]
		chain = self.fat.getFreeClusterChain(5)
		self.assertEqual(5, len(chain))
		for i in chain:
			self.assertEqual(0x0000, self.fat.clustermap[i])
		self.assertEqual(test_chain, chain)

	def test_linkClusterChain(self):
		test_chain = [10205, 10206, 10207]
		self.fat.linkClusterChain(test_chain)
		self.assertEqual(10206, self.fat.clustermap[10205])
		self.assertEqual(10207, self.fat.clustermap[10206])
		self.assertEqual(0xFFFF, self.fat.clustermap[10207])

	def test_pack(self):
		b = self.fat.pack()
		self.assertEqual(65536, len(b))
		self.assertEqual(self.bytes, b)


class TestDirectoryEntry(unittest.TestCase):
	def pack(self):
		byte_name = bytearray(self.filename, 'ascii')
		return struct.pack('BB42sII12x',
						self.namesize,
						self.attributes,
						byte_name+((42-len(byte_name))*b'\xFF'),
						self.cluster,
						self.filesize)

	def setUp(self):
		self.filename = 'TestFileName.test'
		self.namesize = len(self.filename)
		self.attributes = 0
		self.cluster = 0x5454ABAB
		self.filesize = 0x12345678
		self.file = self.pack()

	def test_init_file(self):
		de = DirectoryEntry(self.file, 0)
		self.assertEqual(self.filename, de.filename)
		self.assertFalse(de.atr.READONLY)
		self.assertFalse(de.atr.HIDDEN)
		self.assertFalse(de.atr.SYSTEM)
		self.assertFalse(de.atr.VOLUMELABEL)
		self.assertFalse(de.atr.DIRECTORY)
		self.assertFalse(de.atr.ARCHIVE)
		self.assertFalse(de.atr.DELETED)
		self.assertEqual(self.filesize, de.size)
		self.assertEqual(self.cluster, de.cluster)
		self.assertEqual(self.filename, str(de))

	def test_init_wrong_size(self):
		with self.assertRaises(ValueError):
			DirectoryEntry(self.file+b'\x00', 0)

		with self.assertRaises(ValueError):
			DirectoryEntry(b'\x00', 0)

	def test_init_invalid_name(self):
		self.namesize = 53
		self.file = self.pack()
		with self.assertRaises(SystemError):
			DirectoryEntry(self.file, 0)

	def test_init_end_of_list(self):
		self.namesize = 0xFF
		self.file = self.pack()
		with self.assertRaises(SystemError):
			DirectoryEntry(self.file, 0)

		self.namesize = 0x00
		self.file = self.pack()
		with self.assertRaises(SystemError):
			DirectoryEntry(self.file, 0)

	def test_rename(self):
		de = DirectoryEntry(self.file, 0)
		with self.assertRaises(ValueError):
			de.rename("This name is too long, like, so long, is does not fit in 42 chars")

		test_name = "JFR rocks"
		de.rename(test_name)
		self.assertEqual(test_name, de.filename)
		self.assertEqual(len(test_name), de.namesize)

	def test_pack(self):
		de = DirectoryEntry(self.file, 0)
		self.assertEqual(self.file, de.pack())

		test_name = "JFR rocks"
		de.rename(test_name)
		self.filename = test_name
		self.namesize = len(test_name)
		self.file = self.pack()
		self.assertEqual(self.file, de.pack())

		de.atr.READONLY = True
		de.atr.HIDDEN = False
		de.atr.DIRECTORY = True
		de.atr.DELETED = True
		de = DirectoryEntry(de.pack(), 0)
		self.assertTrue(de.atr.READONLY)
		self.assertFalse(de.atr.HIDDEN)
		self.assertTrue(de.atr.DIRECTORY)
		self.assertTrue(de.atr.DELETED)

	def test_new(self):
		self.filename = 'NewEntry'
		self.namesize = len(self.filename)
		self.attributes = 0
		self.cluster = 0
		self.filesize = 12345
		self.file = self.pack()

		de = DirectoryEntry.new(12345, "NewEntry")
		self.assertEqual(self.file, de.pack())
		
		with self.assertRaises(ValueError):
			DirectoryEntry.new(12345, "This name is too long, like, so long, is does not fit in 42 chars")


class TestDirectoryEntryList(unittest.TestCase):
	def setUp(self):
		self.data = b''
		for i in range(0,100):
			self.data += DirectoryEntry.new(i, "Entry {:02d}".format(i)).pack()
		self.data += b'\xFF'+b'\x00'*63

	def test_init(self):
		el = DirectoryEntryList(self.data, 0)
		self.assertEqual(100, len(el.l))
		self.assertEqual(0, el.clusterID)
		for i, k in enumerate(el.list()):
			self.assertEqual("Entry {:02d}".format(i), k.filename)

	def test_invalid_entrys(self):
		self.data = b'\x32\xab\x00\xFF'*16*5
		with self.assertRaises(SystemError):
			DirectoryEntryList(self.data, 0)

	def test_missing_termination(self):
		self.data = DirectoryEntry.new(0, "Entry").pack()
		self.data *= 5
		with self.assertRaises(SystemError):
			DirectoryEntryList(self.data, 0)

	def test_trailing_data(self):
		self.data += DirectoryEntry.new(0, "Entry").pack()*5
		self.assertEqual(100, len(DirectoryEntryList(self.data, 0).l))

	def test_list(self):
		el = DirectoryEntryList(self.data, 0)
		self.assertEqual(100, len(el.list()))

	def test_append(self):
		el = DirectoryEntryList(self.data, 0)
		de = DirectoryEntry.new(0, "New")
		el.append(de)
		self.assertEqual(101, len(el.list()))
		self.assertIn(de, el.list())

	def test_pack(self):
		el = DirectoryEntryList(self.data, 0)
		self.assertEqual(self.data, el.pack())

		de = DirectoryEntry.new(0, "New")
		el.append(de)
		self.assertIn(de.pack(), el.pack())




