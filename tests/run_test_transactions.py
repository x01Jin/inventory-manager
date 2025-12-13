import tempfile
import shutil
from pathlib import Path
import sys

# Import test modules directly
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path as _P

_root = _P(__file__).parent
# Ensure repository root is in sys.path for imports
sys.path.insert(0, str(_root.parent))
spec = importlib.util.spec_from_file_location(
    "test_transactions", str(_root / "test_transactions.py")
)
assert spec is not None and spec.loader is not None
test_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(test_mod)
test_item_save_commits_with_batch = test_mod.test_item_save_commits_with_batch
test_item_save_rolls_back_on_batch_failure = (
    test_mod.test_item_save_rolls_back_on_batch_failure
)
test_requisition_save_rolls_back_on_movement_failure = (
    test_mod.test_requisition_save_rolls_back_on_movement_failure
)
spec = importlib.util.spec_from_file_location(
    "test_stock_reservations", str(_root / "test_stock_reservations.py")
)
assert spec is not None and spec.loader is not None
stock_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stock_mod)
test_create_stock_movements_insufficient_stock = (
    stock_mod.test_create_stock_movements_insufficient_stock
)
test_create_stock_movements_success = stock_mod.test_create_stock_movements_success
spec = importlib.util.spec_from_file_location(
    "test_deletion_transactions", str(_root / "test_deletion_transactions.py")
)
assert spec is not None and spec.loader is not None
deletion_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deletion_mod)
test_item_delete_rolls_back_on_failure = (
    deletion_mod.test_item_delete_rolls_back_on_failure
)
test_requisition_delete_rolls_back_on_failure = (
    deletion_mod.test_requisition_delete_rolls_back_on_failure
)
spec = importlib.util.spec_from_file_location(
    "test_return_transactions", str(_root / "test_return_transactions.py")
)
assert spec is not None and spec.loader is not None
return_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(return_mod)
test_return_processing_rollback_on_movement_failure = (
    return_mod.test_return_processing_rollback_on_movement_failure
)
spec = importlib.util.spec_from_file_location(
    "test_indexes", str(_root / "test_indexes.py")
)
assert spec is not None and spec.loader is not None
index_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(index_mod)
test_stock_movements_has_source_index = index_mod.test_stock_movements_has_source_index
nested_spec = importlib.util.spec_from_file_location(
    "test_nested_transactions", str(_root / "test_nested_transactions.py")
)
assert nested_spec is not None and nested_spec.loader is not None
nested_mod = importlib.util.module_from_spec(nested_spec)
nested_spec.loader.exec_module(nested_mod)
test_create_stock_movements_nested_transaction_rolls_back_on_failure = (
    nested_mod.test_create_stock_movements_nested_transaction_rolls_back_on_failure
)


def run_all():
    tmpdir = tempfile.mkdtemp()
    try:
        tmp_path = Path(tmpdir)
        print("Running test_item_save_commits_with_batch...")
        test_item_save_commits_with_batch(tmp_path / "case1")
        print("PASS: test_item_save_commits_with_batch")

        # The second test requires monkeypatch; run it with a simple monkeypatch helper
        class SimpleMonkeyPatch:
            def __init__(self):
                self._patches = []

            def setattr(self, target, name, value):
                original = getattr(target, name)
                setattr(target, name, value)
                self._patches.append((target, name, original))
                return original

            def restore_all(self):
                for target, name, original in reversed(self._patches):
                    setattr(target, name, original)
                self._patches.clear()

        mp = SimpleMonkeyPatch()
        print("Running test_item_save_rolls_back_on_batch_failure...")
        test_item_save_rolls_back_on_batch_failure(tmp_path / "case2", mp)
        mp.restore_all()
        print("PASS: test_item_save_rolls_back_on_batch_failure")

        print("Running test_requisition_save_rolls_back_on_movement_failure...")
        test_requisition_save_rolls_back_on_movement_failure(tmp_path / "case3")
        print("PASS: test_requisition_save_rolls_back_on_movement_failure")

        # Run last insert id tests
        print("Running test_last_insert_id tests...")
        last_mod = SourceFileLoader(
            "test_last_insert_id", str(_root / "test_last_insert_id.py")
        ).load_module()
        last_mod.test_execute_update_returns_last_id(tmp_path / "lastid")
        last_mod.test_model_save_sets_id(tmp_path / "lastid")
        print("PASS: test_last_insert_id tests")

        # Run stock reservation tests
        print("Running test_create_stock_movements_insufficient_stock...")
        test_create_stock_movements_insufficient_stock(tmp_path / "stock1")
        print("PASS: test_create_stock_movements_insufficient_stock")

        print("Running test_create_stock_movements_success...")
        test_create_stock_movements_success(tmp_path / "stock2")
        print("PASS: test_create_stock_movements_success")

        print("Running test_item_delete_rolls_back_on_failure...")
        test_item_delete_rolls_back_on_failure(tmp_path / "del1")
        print("PASS: test_item_delete_rolls_back_on_failure")

        print("Running test_requisition_delete_rolls_back_on_failure...")
        test_requisition_delete_rolls_back_on_failure(tmp_path / "del2")
        print("PASS: test_requisition_delete_rolls_back_on_failure")

        print("Running test_return_processing_rollback_on_movement_failure...")
        test_return_processing_rollback_on_movement_failure(tmp_path / "ret1")
        print("PASS: test_return_processing_rollback_on_movement_failure")

        print(
            "Running test_create_stock_movements_nested_transaction_rolls_back_on_failure..."
        )
        test_create_stock_movements_nested_transaction_rolls_back_on_failure(
            tmp_path / "nested1"
        )
        print(
            "PASS: test_create_stock_movements_nested_transaction_rolls_back_on_failure"
        )

        print("Running test_stock_movements_has_source_index...")
        test_stock_movements_has_source_index(tmp_path / "index1")
        print("PASS: test_stock_movements_has_source_index")

    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    run_all()
