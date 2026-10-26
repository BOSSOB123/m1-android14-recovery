import hashlib
import importlib.util
import lzma
import struct
import tempfile
import unittest
import zlib
from pathlib import Path


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] / "tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


image = load("verify_image")
gpt = load("gpt_report")
publication = load("check_publication")


def ext_fixture():
    # Artificial superblock only: intentionally not a complete ext filesystem.
    b = bytearray(4096)
    struct.pack_into("<I", b, 1028, 4)
    struct.pack_into("<I", b, 1048, 0)
    struct.pack_into("<H", b, 1080, 0xEF53)
    return bytes(b)


def gpt_fixture():
    b = bytearray(4096)
    h = 512
    b[h:h + 8] = b"EFI PART"
    struct.pack_into("<IIII", b, h + 8, 0x10000, 92, 0, 0)
    struct.pack_into("<QQQQ", b, h + 24, 1, 99999, 34, 99966)
    struct.pack_into("<QIII", b, h + 72, 2, 4, 128, 0)
    b[1024:1040] = b"\x01" * 16
    b[1040:1056] = b"\x02" * 16
    struct.pack_into("<QQ", b, 1056, 2048, 4095)
    b[1080:1092] = "system".encode("utf-16le")
    update_gpt_crc(b)
    return b


def update_gpt_crc(b):
    struct.pack_into("<I", b, 600, zlib.crc32(b[1024:1536]))
    struct.pack_into("<I", b, 528, 0)
    struct.pack_into("<I", b, 528, zlib.crc32(b[512:604]))


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "fixture"

    def test_raw_and_xz_hash_the_same_expanded_bytes(self):
        data = ext_fixture()
        expected = hashlib.sha256(data).hexdigest()
        self.path.write_bytes(data)
        self.assertEqual(image.inspect_image(self.path, expected)["sha256_raw"], expected)
        self.path.write_bytes(lzma.compress(data))
        self.assertEqual(image.inspect_image(self.path, expected)["expanded_bytes"], len(data))

    def test_rejects_wrong_hash_and_size(self):
        self.path.write_bytes(ext_fixture())
        with self.assertRaisesRegex(ValueError, "SHA256"):
            image.inspect_image(self.path, "0" * 64)
        with self.assertRaisesRegex(ValueError, "exceeds"):
            image.inspect_image(self.path, max_bytes=2048)

    def test_rejects_sparse_and_truncated_filesystem(self):
        self.path.write_bytes(b"\x3a\xff\x26\xed" + bytes(4092))
        with self.assertRaisesRegex(ValueError, "sparse"):
            image.inspect_image(self.path)
        data = bytearray(ext_fixture())
        struct.pack_into("<I", data, 1028, 5)
        self.path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "beyond"):
            image.inspect_image(self.path)

    def test_rejects_corrupt_xz_stream(self):
        data = bytearray(lzma.compress(ext_fixture()))
        data[-12] ^= 0xFF
        self.path.write_bytes(data)
        with self.assertRaises((lzma.LZMAError, EOFError)):
            image.inspect_image(self.path)


class GptTests(unittest.TestCase):
    def test_valid_crc_and_no_guid_output(self):
        result = gpt.inspect_gpt(gpt_fixture())
        self.assertEqual(result["partitions"], [{"index": 1, "name": "system", "offset_bytes": 1048576, "length_bytes": 1048576}])
        self.assertNotIn("uuid", str(result).lower())
        self.assertEqual(result["guid_values"], "intentionally omitted")

    def test_header_corruption(self):
        data = gpt_fixture()
        data[550] ^= 1
        with self.assertRaisesRegex(ValueError, "header CRC"):
            gpt.inspect_gpt(data)

    def test_table_corruption_and_truncation(self):
        data = gpt_fixture()
        data[1100] ^= 1
        with self.assertRaisesRegex(ValueError, "table CRC"):
            gpt.inspect_gpt(data)
        with self.assertRaisesRegex(ValueError, "truncated"):
            gpt.inspect_gpt(gpt_fixture()[:1200])

    def test_out_of_bounds_partition_even_with_valid_crc(self):
        data = gpt_fixture()
        struct.pack_into("<QQ", data, 1056, 100000, 100001)
        update_gpt_crc(data)
        with self.assertRaisesRegex(ValueError, "bounds"):
            gpt.inspect_gpt(data)

    def test_overlapping_partition_even_with_valid_crc(self):
        data = gpt_fixture()
        data[1152:1168] = b"\x03" * 16
        struct.pack_into("<QQ", data, 1184, 3000, 5000)
        update_gpt_crc(data)
        with self.assertRaisesRegex(ValueError, "overlapping"):
            gpt.inspect_gpt(data)


class PublicationTests(unittest.TestCase):
    def test_private_key_and_binary_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "backup.img").write_bytes(b"private")
            (root / "secret.txt").write_text("-----BEGIN " + "PRIVATE KEY-----")
            self.assertEqual(len(publication.problems(root)), 2)


if __name__ == "__main__":
    unittest.main()
