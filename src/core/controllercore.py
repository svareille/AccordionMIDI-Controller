"""Core of the controller.

Contains everything a UI should need.
"""
import os
from typing import Dict, List
from copy import deepcopy

from .origin import Origin
from .arduino import Arduino, midiio
from .keyboard import Keyboard, MidiData
from .json import JsonFile
from .notifications import Notification


class ControllerCore:
    """Core of the controller."""

    def __init__(self):
        self.keyboards = []
        """Keep opened keyboards.
        List[KeyboardState]
        """
        self.arduino = Arduino()
        self.history = History()

    def open(self, filename: str) -> 'KeyboardState':
        """
        Open a file containig a keyboard.

        Parameters
        ----------
        filename : str
            The file to open.

        Returns
        -------
        KeyboardState
            The opened keyboard.

        """
        for kbd in self.keyboards:
            if os.path.samefile(kbd.storage.filename, filename):
                return kbd

        kbd_state = KeyboardState()
        _, ext = os.path.splitext(filename)

        if ext == '.json':
            kbd_state.storage = JsonFile(filename)
        else:
            raise UnknownFileTypeError(f"The file '{filename}' is of unknown "
                                       "type.")

        kbd_state.load()
        self.keyboards.append(kbd_state)
        return kbd_state

    def save_as(self, kbd_state: 'KeyboardState', filename: str):
        """
        Save a keyboard with filename and corresponding file format.

        Parameters
        ----------
        kbd_state : 'KeyboardState'
            The keyboard to save.
        filename : str
            The file.

        Returns
        -------
        None.

        """
        _, ext = os.path.splitext(filename)

        if ext == '.json':
            kbd_state.storage = JsonFile(filename)
        else:
            raise UnknownFileTypeError(f"The file '{filename}' is of unknown "
                                       "type.")
        kbd_state.save()

    def close(self, kbd_state: 'KeyboardState'):
        """
        Close the given keyboard.

        Parameters
        ----------
        kbd_state : 'KeyboardState'
            The keyboard to close.

        Returns
        -------
        None.

        """
        self.keyboards.remove(kbd_state)

    def create(self, kbd_type: type) -> 'KeyboardState':
        """
        Create a new empty keyboard.

        Parameters
        ----------
        kbd_type : type
            The type of the keyboard to create.

        Returns
        -------
        KeyboardState
            The created keyboard.

        """
        kbd_state = KeyboardState(kbd_type())

        self.keyboards.append(kbd_state)
        return kbd_state

    def get_known_keyboards(self, origin: List[Origin] = None
                            ) -> Dict[Origin, List[Keyboard]]:
        """
        Return all known keyboards.

        If `origin` is specified, only keyboards from theses origins will be
        returned.

        Parameters
        ----------
        origin : List[Origin], optional
            The origins from which the keyoards will be returned. If None every
            known keyboard will be returned. The default is None.

        Returns
        -------
        Dict[Origin, List[Keyboard]]
            The keyboards, as a dict. The keys are origins, the values are
            list of Keyboards

        """
        result = dict()
        if origin is None or Origin.Arduino in origin:
            result[Origin.Arduino] = self.arduino.get_stored_keyboards()
            if self.arduino.get_current_left_keyboard():
                result[Origin.Arduino].append(
                    self.arduino.get_current_left_keyboard())
            if self.arduino.get_current_right_keyboard():
                result[Origin.Arduino].append(
                    self.arduino.get_current_right_keyboard())
        return result

    def connect_midi(self, inport=None, outport=None):
        """
        Connect the MIDI ports.

        Parameters
        ----------
        inport : str, optional
            The input port to connect to. The default is None.
        outport : str, optional
            The output port to connect to. The default is None.

        Returns
        -------
        None.

        """
        if inport:
            midiio.connect_input(inport)
        if outport:
            midiio.connect_output(outport)

    def close_midi(self):
        """Close the MIDI ports."""
        midiio.close()

    def is_midi_input_ready(self):
        """Return True if the MIDI input port is ready, False otherwise."""
        return midiio.input_ready()

    def is_midi_output_ready(self):
        """Return True if the MIDI output port is ready, False otherwise."""
        return midiio.input_ready()

    def list_midi_ports(self):
        """
        List all MIDI ports.

        Returns
        -------
        List of str
            The names of the available input ports.
        List of str
            The names of the available output ports.

        """
        return midiio.list_input_ports(), midiio.list_output_ports()
   


class KeyboardState:
    """Keep every infos about a keyboard."""

    def __init__(self, kbd=None):
        self.history = History()
        self.keyboard = kbd
        self.storage = None
        self.is_saved = False
        self.keyboard_changed = Notification()

    def load(self):
        """
        Load keyboard from storage.

        Returns
        -------
        None.

        """
        self.keyboard = self.storage.load()
        self.is_saved = True
        self.keyboard_changed()

    def save(self):
        """
        Save keyboard to storage.

        Returns
        -------
        None.

        """
        self.storage.save(self.keyboard)
        self.is_saved = True
        self.keyboard_changed()

    def store(self):
        """
        Store the keyboard of the Arduino.

        Returns
        -------
        None.

        """

    def set_as_current(self):
        """
        Set the keyboard as current on the Arduino.

        Returns
        -------
        None.

        """

    def rename(self, new_name: str):
        """
        Rename the keyboard.

        Parameters
        ----------
        new_name : str
            The new name.

        Returns
        -------
        None.

        """
        if new_name != self.keyboard.name:
            self.history.execute(RenameKeyboard(self.keyboard, new_name))
            self.is_saved = False
            self.keyboard_changed()

    def set_keyboard_data(self, index, data: MidiData):
        """
        Set the keyboard's data identified by index.

        Parameters
        ----------
        index : undefined
            The index of the data to set.
        data : MidiData
            The data to set.

        Returns
        -------
        None.

        """
        if data != self.keyboard.get_data(index):
            self.history.execute(SetKeyboardData(self.keyboard, index, data))
            self.is_saved = False
            self.keyboard_changed()

    def undo(self):
        """
        Undo previous action.

        Returns
        -------
        None.

        """
        self.history.undo()
        self.keyboard_changed()

    def redo(self):
        """
        Redo previous undoed action.

        Returns
        -------
        None.

        """
        self.history.redo()
        self.keyboard_changed()


class History:
    """Class to keep an history of every action performed."""

    def __init__(self):
        self._commands = list()
        self._redo = list()

    def execute(self, command):
        """
        Execute the specified command and store it in history.

        Parameters
        ----------
        command :
            The command to execute.

        Returns
        -------
        None.

        """
        self._commands.append(command)
        command.execute()
        self._redo.clear()

    def undo(self):
        """
        Undo the pevious command.

        Returns
        -------
        None.

        """
        try:
            command = self._commands.pop()
            self._redo.append(command)
            command.undo()
        except IndexError as err:
            raise NothingToUndoError("There is nothing to undo") from err

    def redo(self):
        """
        Redo the previously undoed command.

        Returns
        -------
        None.

        """
        try:
            command = self._redo.pop()
            self._commands.append(command)
            command.execute()
        except IndexError as err:
            raise NothingToRedoError("There is nothing to redo") from err


class RenameKeyboard():
    def __init__(self, kbd, new_name):
        self.last_name = kbd.name
        self.new_name = new_name
        self.kbd = kbd

    def execute(self):
        self.kbd.name = self.new_name

    def undo(self):
        self.kbd.name = self.last_name


class SetKeyboardData():
    def __init__(self, kbd, index, data):
        self.kbd = kbd
        self.index = index
        self.prev_data = deepcopy(self.kbd.get_data(index))
        self.data = deepcopy(data)

    def execute(self):
        self.kbd.set_data(self.index, self.data)

    def undo(self):
        self.kbd.set_data(self.index, self.prev_data)


class UnknownFileTypeError(Exception):
    pass


class NothingToUndoError(Exception):
    pass

class NothingToRedoError(Exception):
    pass