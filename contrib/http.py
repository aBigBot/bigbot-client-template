from django.http import JsonResponse

from contrib.exceptions import JsonRPCException


class JsonRPCResponse(JsonResponse):
    """Extends JsonResponse to return a response like:

    {
        "id": None,
        "jsonrpc": "2.0",
        "result": result
    }
    """

    def __init__(self, result=None, error=None, id=None, jsonrpc="2.0", status=200):
        """Creates a JsonRPCResponse

        Args:
            result (object): A JSON serializable object.
            error (object): An error object or a list of error objects. An error object must have
                the following structure (data field is optional):
                {"code" CODE_NUMBER, "message": "Error description", "data": <any extra data>}
            id (int): Id or response number. Defaults to None.
            jsonrpc (str): JSONRPC implementation. Defaults to "2.0".
            status (int): HTTP status of the responde. Defaults to 200.
        """
        data = {"id": id, "jsonrpc": jsonrpc, "result": result}
        if error:
            del data["result"]
            if isinstance(error, JsonRPCException):
                data["error"] = dict(error)
            elif isinstance(error, list):
                for index, item in enumerate(error):
                    if isinstance(item, JsonRPCException):
                        error[index] = dict(item)
                    else:
                        error[index] = item
                data["error"] = error
            else:
                data["error"] = str(error)
        super().__init__(data, status=status)
