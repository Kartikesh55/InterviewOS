class InterviewOSException(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ResourceNotFound(InterviewOSException):
    status_code = 404


class LifecycleConflict(InterviewOSException):
    status_code = 409


class QuestionGenerationFailed(InterviewOSException):
    status_code = 502


class InvalidEvaluation(InterviewOSException):
    status_code = 502
