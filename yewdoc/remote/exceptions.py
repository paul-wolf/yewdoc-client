class RemoteException(Exception):
    """Custom exception for remote errors."""
    pass

class OfflineException(Exception):
    """Raised if remote operation attempted when offline."""

    pass

