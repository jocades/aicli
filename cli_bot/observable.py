from abc import ABC, abstractmethod


class Observer(ABC):
    @abstractmethod
    def update(self, observable, *args, **kwargs):
        ...


class Observable(ABC):
    def __init__(self, observers: list[Observer] = []):
        self._observers = observers

    def add_observer(self, observer):
        self._observers.append(observer)

    def remove_observer(self, observer):
        self._observers.remove(observer)

    def notify_observers(self, *args, **kwargs):
        for observer in self._observers:
            observer.update(self, *args, **kwargs)
