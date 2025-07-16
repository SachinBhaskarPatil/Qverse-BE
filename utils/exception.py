from rest_framework.exceptions import APIException

class InternalServerError(APIException):
    status_code = 500


class BadRequest(APIException):
    status_code = 400


class UnAuthorized(APIException):
    status_code = 401


class Forbidden(APIException):
    status_code = 403


class NotFound(APIException):
    status_code = 404
