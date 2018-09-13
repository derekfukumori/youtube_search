import json

class Album:
    source = None
    id = None
    artists = None
    title = None
    publisher = None
    tracks = []
    #self.date = None #TODO
    def __repr__(self):
        s = {'source': self.source,
             'id': self.id,
             'artists': self.artists,
             'title': self.title,
             'publisher': self.publisher
            }
        return json.dumps(s)

class Track:
    source = None
    id = None
    artists = None
    title = None
    duration = None
    ordinal = None
    def __repr__(self):
        s = {'source': self.source,
             'id': self.id,
             'artists': self.artists,
             'title': self.title,
             'duration': self.duration,
             'ordinal' : self.ordinal
            }
        return json.dumps(s)