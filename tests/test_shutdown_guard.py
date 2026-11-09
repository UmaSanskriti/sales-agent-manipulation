import pytest

from scripts.watch_generation import matching_instance, stop_reason


def test_does_not_delete_reused_instance_id():
    with pytest.raises(ValueError, match='identity changed'):
        matching_instance([{'id': '0', 'name': 'other', 'uuid': 'other'}], '0', 'ours')
    assert matching_instance([], '0', 'ours') is None
    item = {'id': '0', 'name': 'ours', 'uuid': 'ours'}
    assert matching_instance([item], '0', 'ours') == item


def test_completion_and_failure_limits():
    assert stop_reason(600, 600, 500, 0, 21600, 1200) == 'all_expected_files_saved'
    assert stop_reason(300, 600, 21600, 0, 21600, 1200) == 'runtime_limit'
    assert stop_reason(300, 600, 5000, 1200, 21600, 1200) == 'no_file_progress'
    assert stop_reason(300, 600, 5000, 60, 21600, 1200) is None
