from abc import ABC, abstractmethod


class TradingSession(ABC):
    """
    Interface to a live or backtested trading session.
    """

    @abstractmethod
    def run(self):
        raise NotImplementedError(
            "Should implement run()"
        )
