from abc import ABC
from abc import abstractmethod


class BaseRTCProvider(ABC):

    # =====================================================
    # CREATE ROOM
    # =====================================================

    @abstractmethod
    def create_room(
        self,
        *,
        room_name,
    ):
        pass

    # =====================================================
    # DELETE ROOM
    # =====================================================

    @abstractmethod
    def delete_room(
        self,
        *,
        room_name,
    ):
        pass

    # =====================================================
    # GENERATE TOKEN
    # =====================================================

    @abstractmethod
    def generate_token(
        self,
        *,
        room_name,
        participant_identity,
        participant_name,
        metadata=None,
    ):
        pass