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

    def script_filters(self):
        root = Path(__file__).resolve().parents[1]
        with (root / "info.plist").open("rb") as plist:
            metadata = plistlib.load(plist)
        return [
            item
            for item in metadata["objects"]
            if item["type"] == "alfred.workflow.input.scriptfilter"
        ]

    def test_script_filters_use_launcher_not_python_shebang(self):
        scripts = {item["config"]["script"] for item in self.script_filters()}

        self.assertEqual(len(scripts), 1)
        self.assertIn('./run_fkill.sh filter "$1"', scripts)

    def test_script_filter_matches_axe_keyword_entry_pattern(self):
        query_filter = next(
            item
            for item in self.script_filters()
            if item["config"]["script"] == './run_fkill.sh filter "$1"'
        )

        self.assertEqual(query_filter["config"]["keyword"], "fkill")
        self.assertTrue(query_filter["config"]["withspace"])
        self.assertEqual(query_filter["config"]["argumenttype"], 1)
        self.assertTrue(query_filter["config"]["argumenttreatemptyqueryasnil"])

    def test_script_filters_run_as_zsh(self):
        for script_filter in self.script_filters():
            self.assertEqual(script_filter["config"]["type"], 11)

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
