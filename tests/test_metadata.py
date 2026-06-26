import plistlib
from pathlib import Path
import unittest


class MetadataTests(unittest.TestCase):
    def test_bundle_id_uses_public_github_namespace(self):
        root = Path(__file__).resolve().parents[1]
        with (root / "info.plist").open("rb") as plist:
            metadata = plistlib.load(plist)

        self.assertEqual(metadata["bundleid"], "com.z4jst.alfred.fkill")


if __name__ == "__main__":
    unittest.main()
