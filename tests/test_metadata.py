import plistlib
import zipfile
from pathlib import Path
import unittest


class MetadataTests(unittest.TestCase):
    def test_bundle_id_uses_public_github_namespace(self):
        root = Path(__file__).resolve().parents[1]
        with (root / "info.plist").open("rb") as plist:
            metadata = plistlib.load(plist)

        self.assertEqual(metadata["bundleid"], "com.z4jst.alfred.fkill")

    def test_import_metadata_uses_tools_category_and_z4jst_author(self):
        root = Path(__file__).resolve().parents[1]
        with (root / "info.plist").open("rb") as plist:
            metadata = plistlib.load(plist)

        self.assertEqual(metadata["category"], "Tools")
        self.assertEqual(metadata["createdby"], "z4jst")

    def test_script_filter_uses_launcher_not_python_shebang(self):
        root = Path(__file__).resolve().parents[1]
        with (root / "info.plist").open("rb") as plist:
            metadata = plistlib.load(plist)

        script_filter = metadata["objects"][0]
        self.assertEqual(script_filter["config"]["script"], './run_fkill.sh filter "$1"')

    def test_script_filter_runs_without_requiring_a_trailing_space(self):
        root = Path(__file__).resolve().parents[1]
        with (root / "info.plist").open("rb") as plist:
            metadata = plistlib.load(plist)

        script_filter = metadata["objects"][0]
        self.assertFalse(script_filter["config"]["withspace"])

    def test_package_contains_launcher_and_icon(self):
        root = Path(__file__).resolve().parents[1]
        package = root / "dist" / "fkill.alfredworkflow"
        if not package.exists():
            self.skipTest("Run scripts/package.sh before package assertions")

        with zipfile.ZipFile(package) as workflow:
            names = set(workflow.namelist())

        self.assertIn("run_fkill.sh", names)
        self.assertIn("icon.png", names)


if __name__ == "__main__":
    unittest.main()
