import time

from sma.storage import save
from sma.state import state


class SaveService:

    def run(self):

        while True:

            if state.is_dirty():

                save(state.get())

                state.clear_dirty()

            time.sleep(1)
