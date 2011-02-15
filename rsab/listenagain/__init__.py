
config = None

class ListenAgainError(StandardError):
    pass

class ListenAgainConfigError(ListenAgainError):
    pass

class ListenAgainUsageError(ListenAgainError):
    pass

class ListenAgainDataError(ListenAgainError):
    pass
