import pytest
from pydantic import ValidationError

from codelens.settings import Settings


def test_retention_cannot_delete_all_data_by_negative_age():
    with pytest.raises(ValidationError):
        Settings(retention_days=-1)


def test_empty_allowlist_denies_all():
    assert not Settings(allowed_repositories="").allows("test/repository")


def test_allowlist_uses_exact_case_insensitive_names():
    config = Settings(allowed_repositories=" Owner/Repository, another/repo ")
    assert config.allows("owner/repository")
    assert not config.allows("owner/repository-other")


@pytest.mark.parametrize(
    "field,value",
    [
        ("admin_token", "replace-with-a-random-token-at-least-32-characters"),
        ("webhook_secret", "replace-with-another-random-secret"),
    ],
)
def test_example_credentials_fail_closed_without_logging_values(field, value):
    with pytest.raises(ValidationError) as error:
        Settings(**{field: value})
    assert value not in str(error.value)
    assert "Replace example credentials" in str(error.value)
