# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Built-in modules
import ctypes
import os
import platform
import sys

# Windows specific third-party modules
try:
	import win32gui
	import win32com.client
	import pywintypes
except ImportError:
	pass

# Darwin specific third-party modules
try:
	# For Mac OS X, we need the NSSpeechSynthesizer class from the Cocoa module
	from Cocoa import NSSpeechSynthesizer
except ImportError:
	pass

# determine the directory where the screen reader API DLL files are stored, even if Python is running through a frozen Py2EXE.
try:
	if sys.frozen or sys.importers:
		LIB_DIRECTORY = os.path.join(os.path.dirname(sys.executable), "speech_libs")
except AttributeError:
	LIB_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "speech_libs")

DOLACCESS_NONE = 0
DOLACCESS_SPEAK = 1
DOLACCESS_MUTE = 141


class Speech(object):
	def __init__(self):
		if platform.system() == "Windows":
			if platform.architecture()[0] == "32bit":
				self.dolphin_api = ctypes.windll.LoadLibrary(os.path.join(LIB_DIRECTORY, "dolapi32.dll"))
				self.nvda_api = ctypes.windll.LoadLibrary(os.path.join(LIB_DIRECTORY, "nvdaControllerClient32.dll"))
				self.sa_api = ctypes.windll.LoadLibrary(os.path.join(LIB_DIRECTORY, "SAAPI32.dll"))
			else:
				self.nvda_api = ctypes.windll.LoadLibrary(os.path.join(LIB_DIRECTORY, "nvdaControllerClient64.dll"))
				self.sa_api = ctypes.windll.LoadLibrary(os.path.join(LIB_DIRECTORY, "SAAPI64.dll"))
			try:
				self.dolphin_api.DolAccess_Command.argtypes = (ctypes.c_wchar_p, ctypes.c_int, ctypes.c_int)
				self.dolphin_api.DolAccess_Action.argtypes = (ctypes.c_int,)
			except AttributeError:
				pass
			self.nvda_api.nvdaController_speakText.argtypes = (ctypes.c_wchar_p,)
			self.sa_api.SA_SayW.argtypes = (ctypes.c_wchar_p,)
			try:
				self.ms_sapi = win32com.client.Dispatch("SAPI.SpVoice")
			except pywintypes.com_error:
				self.ms_sapi = None
		elif platform.system() == "Darwin":
			# Allocate and initialize the default TTS
			self.MacTTS = NSSpeechSynthesizer.alloc().init()

	def darwin_running(self):
		try:
			return bool(self.MacTTS)
		except:
			return False

	def darwin_say(self, text, interrupt=False):
		if interrupt:
			self.MacTTS.stopSpeaking()
		self.MacTTS.startSpeakingString_(text)

	def darwin_silence(self):
		self.MacTTS.stopSpeaking()

	def dolphin_running(self):
		try:
			return self.dolphin_api.DolAccess_GetSystem() != DOLACCESS_NONE
		except:
			return False

	def dolphin_say(self, text, interrupt=False):
		if interrupt:
			self.dolphin_api.DolAccess_Action(DOLACCESS_MUTE)
		self.dolphin_api.DolAccess_Command(text, len(text) * 2 + 2, DOLACCESS_SPEAK)

	def dolphin_silence(self):
		self.dolphin_api.DolAccess_Action(DOLACCESS_MUTE)

	def jfw_running(self):
		try:
			return bool(win32gui.FindWindow("JFWUI2", None))
		except:
			return False

	def jfw_say(self, text, interrupt=False):
		try:
			jfw_api = win32com.client.Dispatch("FreedomSci.JawsApi")
		except pywintypes.com_error:
			return
		jfw_api.SayString(text, bool(interrupt))

	def jfw_silence(self):
		try:
			jfw_api = win32com.client.Dispatch("FreedomSci.JawsApi")
		except pywintypes.com_error:
			return
		jfw_api.StopSpeech()

	def nvda_running(self):
		try:
			return self.nvda_api.nvdaController_testIfRunning()==0
		except:
			return False

	def nvda_say(self, text, interrupt=False):
		if interrupt:
			self.nvda_api.nvdaController_cancelSpeech()
		self.nvda_api.nvdaController_speakText(text)

	def nvda_silence(self):
		self.nvda_api.nvdaController_cancelSpeech()

	def sa_running(self):
		try:
			return bool(self.sa_api.SA_IsRunning())
		except:
			return False

	def sa_say(self, text, interrupt=False):
		if interrupt:
			self.sa_api.SA_StopAudio()
		self.sa_api.SA_SayW(str(text))

	def sa_silence(self):
		self.sa_api.SA_StopAudio()

	def sapi_running(self):
		try:
			return self.ms_sapi is not None
		except:
			return False

	def sapi_say(self, text, interrupt=False):
		self.ms_sapi.Speak(text, 3 if interrupt else 1)

	def sapi_silence(self):
		self.ms_sapi.Speak("", 3)

	def we_running(self):
		try:
			return bool(win32gui.FindWindow("GWMExternalControl", "External Control"))
		except:
			return False

	def we_say(self, text, interrupt=False):
		try:
			we_api = win32com.client.Dispatch("GWSpeak.Speak")
		except pywintypes.com_error:
			return
		if interrupt:
			we_api.Silence()
		we_api.SpeakString(text)

	def we_silence(self):
		try:
			we_api = win32com.client.Dispatch("GWSpeak.Speak")
		except pywintypes.com_error:
			return
		we_api.Silence()

	def say(self, text, interrupt=False):
		if self.darwin_running():
			self.darwin_say(text, interrupt)
		elif self.nvda_running():
			self.nvda_say(text, interrupt)
		elif self.sa_running():
			self.sa_say(text, interrupt)
		elif self.dolphin_running():
			self.dolphin_say(text, interrupt)
		elif self.we_running():
			self.we_say(text, interrupt)
		elif self.jfw_running():
			self.jfw_say(text, interrupt)
		elif self.sapi_running():
			self.sapi_say(text, interrupt)

	def silence(self):
		if self.darwin_running():
			self.darwin_silence()
		elif self.nvda_running():
			self.nvda_silence()
		elif self.sa_running():
			self.sa_silence()
		elif self.dolphin_running():
			self.dolphin_silence()
		elif self.we_running():
			self.we_silence()
		elif self.jfw_running():
			self.jfw_silence()
		elif self.sapi_running():
			self.sapi_silence()


if __name__ == "__main__":
	speaker = Speech()
	speaker.say("hello world!")
