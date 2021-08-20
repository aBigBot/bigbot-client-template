class JsonRPCException(Exception):
    """Exception for JsonRPCRequests

    Attributes:
        code (str): Unique code for the error.
        data (object): Any JSON serializable object required to add more context to the error. Can
            be omitted.
        message (str): Description of the error.
    """

    def __init__(self, message, code=None, data=None):
        self.code = code
        self.data = data
        self.message = message
        super().__init__(message)

    def __iter__(self):
        d = {"code": self.code, "message": self.message}
        if self.data:
            d["data"] = self.data
        for key, item in d.items():
            yield key, item
