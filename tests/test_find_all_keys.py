import importlib.util
from pathlib import Path
import sys
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "wechat-decrypt" / "find_all_keys.py"


def load_module():
    sys.path.insert(0, str(MODULE_PATH.parent))
    spec = importlib.util.spec_from_file_location("find_all_keys", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FindAllKeysTests(unittest.TestCase):
    def test_scan_all_weixin_processes_until_verified_key_found(self):
        module = load_module()
        salt_hex = "b" * 32
        db_files = [("message\\message_0.db", "salt-a", 1, salt_hex, b"page-1")]
        salt_to_dbs = {salt_hex: ["message\\message_0.db"]}

        open_calls = []

        def fake_open_process(mask, inherit, pid):
            open_calls.append(pid)
            return pid

        closed_handles = []

        def fake_close_handle(handle):
            closed_handles.append(handle)
            return True

        verify_calls = []

        def fake_verify(enc_key, page1):
            verify_calls.append((enc_key.hex(), page1))
            return len(verify_calls) == 2

        with mock.patch.object(module, "enum_regions", return_value=[(0x1000, 0x100)]), \
             mock.patch.object(
                 module,
                 "read_mem",
                 return_value=f"x'{'a' * 64}{salt_hex}'".encode(),
             ), \
             mock.patch.object(module.kernel32, "OpenProcess", side_effect=fake_open_process), \
             mock.patch.object(module.kernel32, "CloseHandle", side_effect=fake_close_handle), \
             mock.patch.object(module, "verify_key_for_db", side_effect=fake_verify):
            key_map = module.scan_processes_for_keys(
                db_files=db_files,
                salt_to_dbs=salt_to_dbs,
                pids=[(111, 100), (222, 90)],
            )

        self.assertEqual(
            key_map,
            {salt_hex: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
        )
        self.assertEqual(open_calls, [111, 222])
        self.assertEqual(closed_handles, [111, 222])


if __name__ == "__main__":
    unittest.main()
