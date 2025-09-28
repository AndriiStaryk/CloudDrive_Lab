import pytest
import sys

if __name__ == "__main__":
    # Запускаємо тести
    exit_code = pytest.main([
        "tests/",
        "-v",
        "--tb=short"
    ])
    sys.exit(exit_code)