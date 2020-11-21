from enum import Enum

class RemoteStatus(Enum):
    STATUS_UNKNOWN = -2    
    STATUS_NO_CONNECTION = -1
    STATUS_REMOTE_SAME = 0
    STATUS_REMOTE_NEWER = 1
    STATUS_REMOTE_OLDER = 2
    STATUS_DOES_NOT_EXIST = 3
    STATUS_REMOTE_DELETED = 4

STATUS_MSG = {
    RemoteStatus.STATUS_UNKNOWN: "unknown",    
    RemoteStatus.STATUS_NO_CONNECTION: "can't connect",
    RemoteStatus.STATUS_REMOTE_SAME: "documents are the same",
    RemoteStatus.STATUS_REMOTE_NEWER: "remote is newer",
    RemoteStatus.STATUS_REMOTE_OLDER: "remote is older",
    RemoteStatus.STATUS_DOES_NOT_EXIST: "remote does not exist",
    RemoteStatus.STATUS_REMOTE_DELETED: "remote was deleted",
}
