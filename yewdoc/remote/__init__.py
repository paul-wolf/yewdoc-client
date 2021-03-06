from .constants import RemoteStatus, STATUS_MSG
from .remote import Remote
from .s3remote import RemoteS3
from .exceptions import OfflineException, RemoteException

REMOTES = {"RemoteREST": Remote, "RemoteS3": RemoteS3}
