class Tag(object):
    def __init__(self, store, location, tagid, name):
        self.store = store
        self.location = location
        self.tagid = tagid
        self.name = name

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return self.name


class TagDoc(object):
    def __init__(self, store, tagid, uid):
        self.store = store
        self.tagid = tagid
        self.uid = uid
