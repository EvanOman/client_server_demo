"""Simple test to verify pytest setup."""



def test_simple():
    """Simple test that should always pass."""
    assert 1 + 1 == 2


def test_import_app():
    """Test that we can import the app module."""
    from app.main import create_app
    app = create_app()
    assert app is not None
