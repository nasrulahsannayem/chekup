"""Tests for chekup.monitoring modules."""
from chekup.monitoring.services import get_all_services, get_service_status
from chekup.monitoring.containers import get_container_statuses
from chekup.monitoring.healthchecks import check_url


def test_get_service_status_unknown():
    status = get_service_status("nonexistent-service-12345")
    assert status == "unknown"


def test_get_all_services_empty():
    result = get_all_services(custom=[], auto_discover=False)
    assert isinstance(result, dict)
    assert len(result) == 0


def test_get_container_statuses_nonexistent():
    result = get_container_statuses(["nonexistent-container-12345"])
    assert len(result) == 1
    assert result[0]["state"] == "not found"


def test_check_url_dead():
    result = check_url("http://192.0.2.1:99999", timeout=0.5)
    assert result["ok"] is False
    assert result["error"] is not None
