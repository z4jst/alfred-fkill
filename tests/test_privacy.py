from pathlib import Path
import unittest


class PrivacyTests(unittest.TestCase):
    def test_source_files_do_not_contain_local_identity_markers(self):
        root = Path(__file__).resolve().parents[1]
        forbidden = [
            "jian" + "qi",
            "/" + "Users",
            "软件" + "开发项目",
            "Docu" + "ments",
            "com." + "jian" + "qi",
        ]
        source_files = [
            path
            for path in root.rglob("*")
            if path.is_file()
            and ".git" not in path.parts
            and "__pycache__" not in path.parts
            and "dist" not in path.parts
        ]

        leaks = []
        for path in source_files:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for marker in forbidden:
                if marker in text:
                    leaks.append(f"{path.relative_to(root)} contains {marker}")

        self.assertEqual(leaks, [])


if __name__ == "__main__":
    unittest.main()
