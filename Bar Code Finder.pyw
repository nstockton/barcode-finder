# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Built-in modules
import codecs
import json
import os
import platform
import socket
from threading import Thread
from urllib2 import Request, urlopen
from urllib import urlencode
import webbrowser
try:
	import xml.etree.cElementTree as ET
except ImportError:
	import xml.etree.ElementTree as ET

# Third-party modules
import wx
import wx.lib.dialogs

# Local modules
try:
	from auth import KEY, TOKEN
except ImportError:
	KEY = ""
	TOKEN = ""
from constants import APP_NAME, APP_VERSION, APP_AUTHOR, REF, AGENT, API_URL, MAX_HISTORY, HISTORY_FILE, AUTH_FILE, WINDOW_WIDTH, WINDOW_HEIGHT
from logindialog import LogInDialog
import speech

socket.setdefaulttimeout(10)

if platform.system() == "Windows":
	from win32com.shell import shellcon, shell            
	APP_DATA_DIRECTORY = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)
	APP_DATA_DIRECTORY = os.path.join(APP_DATA_DIRECTORY, APP_NAME)

try:
	with open("sounds/multiple_choice.wav", "rb") as data:
		CHOICE_SND = data.read()
except IOError:
	CHOICE_SND = None

try:
	f = open(HISTORY_FILE, "ab")
	f.close()
except:
	if not os.path.isdir(APP_DATA_DIRECTORY):
		os.makedirs(APP_DATA_DIRECTORY)
	HISTORY_FILE = os.path.join(APP_DATA_DIRECTORY, HISTORY_FILE)
	AUTH_FILE = os.path.join(APP_DATA_DIRECTORY, AUTH_FILE)


class MainFrame(wx.Frame):
	def menu_bind(self, item, handler):
		"""convenience function for binding a method to a menu item"""
		self.Bind(wx.EVT_MENU, handler, item)

	def __init__(self, *args, **kwargs):
		wx.Frame.__init__(self, None, title=APP_NAME, size=(WINDOW_WIDTH, WINDOW_HEIGHT))
		self.Center()
		self.MenuBar = wx.MenuBar()
		self.SetMenuBar(self.MenuBar)
		self.MenuFile = wx.Menu()
		self.MenuHistory = wx.Menu()
		self.MenuHelp = wx.Menu()
		self.MenuBar.Append(self.MenuFile, "&File")
		try:
			with codecs.open(AUTH_FILE, "rb", encoding="utf-8") as data:
				auth = json.load(data)
			(self.uid, self.password, self.is_authorized) = auth
		except:
			self.uid = ""
			self.password = ""
			self.is_authorized = False
		text = "&Logout" if self.is_authorized else "&Login"
		self.menu_bind(self.MenuFile.Append(wx.ID_ANY, text), self.authorize_event)
		self.menu_bind(self.MenuFile.Append(wx.ID_ANY, "E&xit"), self.exit_event)
		self.MenuBar.Append(self.MenuHistory, "Histor&y")
		try:
			with codecs.open(HISTORY_FILE, "rb", encoding="utf-8") as data:
				history_list = json.load(data)
			for (ean, name) in history_list:
				self.menu_bind(self.MenuHistory.Append(wx.ID_ANY, name, ean), self.history_event)
		except:
			history_list = []
		if history_list:
			self.menu_bind(self.MenuHistory.Append(wx.ID_ANY, "Clear History", "Clears the history list."), self.clear_history_event)
		else:
			empty = self.MenuHistory.Append(wx.ID_ANY, "Empty...")
			empty.Enable(False)
		self.MenuBar.Append(self.MenuHelp, "&Help")
		self.menu_bind(self.MenuHelp.Append(wx.ID_ANY, "Visit &BCScan"), self.goto_bcscan_event)
		self.menu_bind(self.MenuHelp.Append(wx.ID_ANY, "Visit &DirectionsForMe"), self.goto_d4me_event)
		self.menu_bind(self.MenuHelp.Append(wx.ID_ANY, "Check For &Updates"), self.update_event)
		self.menu_bind(self.MenuHelp.Append(wx.ID_ANY, "&About %s" % APP_NAME), self.about_event)
		self.Panel = wx.Panel(self, wx.ID_ANY)
		self.Bind(wx.EVT_CHAR_HOOK, self.on_key_event)
		self.LabelBarcode = wx.StaticText(self.Panel, wx.ID_ANY, "&Bar Code:")
		self.InputArea = wx.TextCtrl(self.Panel, style=wx.TE_PROCESS_ENTER)
		self.InputArea.Bind(wx.EVT_TEXT_ENTER, self.search_event)
		self.LabelChoice = wx.StaticText(self.Panel, wx.ID_ANY, "&Result Selection:")
		self.Choice = wx.Choice(self.Panel, wx.ID_ANY, (100, 50), choices=[])
		self.Choice.Bind(wx.EVT_CHOICE, self.choice_event, self.Choice)
		self.LabelChoice.Disable()
		self.Choice.Disable()
		self.LabelOutputArea = wx.StaticText(self.Panel, wx.ID_ANY, "Result &Details:")
		self.OutputArea = wx.TextCtrl(self.Panel, style = wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_NOHIDESEL)
		self.source_button_label = "&Source:"
		self.SourceButton = wx.Button(self.Panel, label=self.source_button_label)
		self.SourceButton.Bind(wx.EVT_BUTTON, self.source_event)
		self.SourceButton.Disable()
		self.EditButton = wx.Button(self.Panel, label = "&Edit BCScan.com Item Info")
		self.EditButton.Bind(wx.EVT_BUTTON, self.edit_event)
		self.EditButton.Disable()
		self.SB = wx.StatusBar(self.Panel)
		self.HorizontalBox = wx.BoxSizer()
		self.HorizontalBox.Add(self.LabelBarcode)
		self.HorizontalBox.Add(self.InputArea, proportion=1, border=1)
		self.HorizontalBox.Add(self.SourceButton, proportion=3, border=1)
		self.HorizontalBox.Add(self.EditButton, proportion=2, border=1)
		self.ChoiceBox = wx.BoxSizer()
		self.ChoiceBox.Add(self.LabelChoice)
		self.ChoiceBox.Add(self.Choice, proportion=1, flag=wx.EXPAND, border=0)
		self.StatusBarBox = wx.BoxSizer()
		self.StatusBarBox.Add(self.SB, proportion=1, border=0)
		self.VerticalBox = wx.BoxSizer(wx.VERTICAL)
		self.VerticalBox.Add(self.HorizontalBox, proportion=0, flag=wx.EXPAND, border=0)
		self.VerticalBox.Add(self.ChoiceBox, proportion=0, flag=wx.EXPAND, border=0)
		self.VerticalBox.Add(self.LabelOutputArea)
		self.VerticalBox.Add(self.OutputArea, proportion=9, flag=wx.EXPAND, border=0)
		self.VerticalBox.Add(self.StatusBarBox, proportion=1, flag=wx.EXPAND, border=0)
		self.Panel.SetSizer(self.VerticalBox)
		self.Show()
		self.SB.SetStatusText(" ")
		self.OutputArea.SetValue("Please set focus to the Bar Code edit box, and scan an item to look up information for a product.")
		self.source_names = []
		self.source_urls = []
		self.results = []
		self.ean = ""
		self.tts = speech.Speech()

	def authorize_event(self, event):
		i = self.MenuFile.FindItemById(event.GetId())
		i_text = i.GetText()
		if i_text == "&Login":
			is_authorized = False
			while not is_authorized:
				DLG = LogInDialog(self, "Login To BCScan.com", "Please enter your login credentials for BCScan.com.")
				modal = DLG.ShowModal()
				DLG.Destroy()
				if modal == wx.ID_CANCEL:
					return
				(uid, password) = DLG.GetValue()
				invalid_msg = "The username or password was invalid.  Please Try again."
				if not uid or not password: 
					self.notify("error", invalid_msg)
					continue
				params = {
					"uid": uid,
					"pass": password,
				}
				req = Request(url="%slookup&%s" % (API_URL, urlencode(params)))
				req.add_header("User-Agent", AGENT)
				try:
					data = urlopen(req)
				except IOError as e:
					if hasattr(e, "reason"):
						msg = "\tServer is unreachable!\nMake sure you are connected to the internet."
					elif hasattr(e, "code"):
						msg = "The server couldn't fulfill the request. (Error "+str(e.code)+")"
					else:
						msg = "Unknown IO Error."
					return self.notify("error", msg)
				try:
					xml = ET.parse(data)
				except ET.ParseError:
					return self.notify("error", "Invalid XML feed.")
				data.close()
				is_authorized = xml.findtext("./query/auth")=="1"
				if not is_authorized:
					self.notify("error", invalid_msg)
			auth = (uid, password, is_authorized)
			(self.uid, self.password, self.is_authorized) = auth
			i.SetText("&Logout")
			self.notify("information", "You are now logged in.", "Information Accepted.")
		elif i_text == "&Logout":
			auth = ("", "", False)
			(self.uid, self.password, self.is_authorized) = auth
			i.SetText("&Login")
			answer = self.notify("question", "Would you like %s to forget your stored login credentials for BCScan.com?" % APP_NAME, "You're logged out.")
			if not answer:
				return
			self.notify("information", "Your login credentials for BCScan.com have been cleared from %s." % APP_NAME, "Success!")
		try:
			with codecs.open(AUTH_FILE, "wb", encoding="utf-8") as data:
				json.dump(auth, data, sort_keys=True, indent=2, separators=(",", ": "))
		except IOError:
			self.notify("error", "Couldn't save the login credentials to disk.")

	def on_key_event(self, event):
		"""When a user presses a key, evaluate it."""
		keycode = event.GetKeyCode()
		if keycode == wx.WXK_CONTROL:
			self.tts.silence()
		else:
			event.Skip()

	def update_event(self, event):
		"""Starts an update check for the program in a new thread."""
		t = Thread(target=self._update)
		t.setDaemon(True)
		t.start()

	def _update(self):
		"""Checks for updates to the program on BCScan.com"""
		params = {"ref": REF}
		req = Request(url="%sversion" % API_URL)
		req.add_header("User-Agent", AGENT)
		req.add_data(urlencode(params))
		try:
			data = urlopen(req)
		except IOError as e:
			if hasattr(e, "reason"):
				msg = "\tThe server is unreachable!\nMake sure you are connected to the internet."
			elif hasattr(e, "code"):
				msg = "The server couldn't fulfill the request. (Error "+str(e.code)+")"
			else:
				msg = "Unknown IO Error."
			return self.notify("error", msg)
		try:
			xml = ET.parse(data)
		except ET.ParseError:
			return self.notify("error", "The server didn't send a valid response.")
		data.close()
		err_msg = xml.findtext("./results/err_msg")
		if err_msg:
			return self.notify("error", err_msg)
		latest_version = xml.findtext("./results/latest_version")
		if not latest_version:
			return self.notify("error", "The server did not return the latest version.")
		try:
			latest_version = float(latest_version)
		except ValueError:
			return self.notify("error", "The server didn't send a valid version number.")
		if float(APP_VERSION) < latest_version:
			dlg = wx.MessageDialog(self, "\t%s version %s is now available.\t\n\tWould you like to go to the download page?" % (APP_NAME, latest_version), "New Version Available", wx.YES | wx.NO | wx.ICON_INFORMATION)
			confirmed = dlg.ShowModal()==wx.ID_YES
			dlg.Destroy()
			if confirmed:
				return webbrowser.open("http://www.bcscan.com/software.php#barcodefinder")
		else:
			self.notify("information", "You are running the latest version of %s\t\n\t\t(version %s)." % (APP_NAME, APP_VERSION), "%s Is Up To Date" % APP_NAME)

	def notify(self, msg_type, msg_text, msg_title=""):
		"""Display a notification to the user."""
		if not msg_title:
			msg_title = msg_type.capitalize()
		if msg_type == "question":
			NotifyBox = wx.MessageDialog(self, message=msg_text, caption=msg_title, style=wx.ICON_QUESTION|wx.YES_NO)
			modal = NotifyBox.ShowModal()
			NotifyBox.Destroy()
			answer = True if modal==wx.ID_YES else False
			return answer
		elif msg_type == "error":
			NotifyBox = wx.MessageDialog(self, message=msg_text, caption=msg_title, style=wx.ICON_ERROR|wx.OK)
		elif msg_type == "information":
			NotifyBox = wx.MessageDialog(self, message=msg_text, caption=msg_title, style=wx.ICON_INFORMATION|wx.OK)
		elif msg_type == "scrolled":
			NotifyBox = wx.lib.dialogs.ScrolledMessageDialog(self, msg_text, msg_title)
		if NotifyBox.ShowModal() == wx.ID_OK:
			NotifyBox.Destroy()

	def history_event(self, event):
		"""Search for the item selected in the history menu."""
		ean = self.MenuHistory.GetHelpString(event.GetId())
		self.InputArea.SetValue(ean)
		self.search_event(event.GetEventObject())

	def save_history(self, history_list=[]):
		"""Saves the history list to a file."""
		try:
			with codecs.open(HISTORY_FILE, "wb", encoding="utf-8") as data:
				json.dump(history_list, data, sort_keys=True, indent=2, separators=(",", ": "))
		except IOError:
			pass

	def clear_history_event(self, event):
		"""Clears the history menu and file."""
		answer = self.notify("question", "Are you shore you want to clear the history list?", "Confirm")
		if not answer:
			return
		for i in self.MenuHistory.GetMenuItems():
			self.MenuHistory.DestroyId(i.GetId())
		empty = self.MenuHistory.Append(wx.ID_ANY, "Empty...")
		empty.Enable(False)
		self.save_history()
		self.notify("information", "Your history list has been cleared.", "Success!")

	def choice_event(self, event):
		"""Update the details box when the selection is changed."""
		wx.CallAfter(self.SourceButton.SetLabel, self.source_button_label)
		wx.CallAfter(self.SourceButton.Disable)
		i = event.GetSelection()
		wx.CallAfter(self.OutputArea.SetValue, self.results[i])
		if self.source_names[i] and self.source_urls[i]:
			wx.CallAfter(self.SourceButton.Enable)
			wx.CallAfter(self.SourceButton.SetLabel, "%s %s" % (self.source_button_label, self.source_names[i]))

	def source_event(self, event):
		"""Open the default web browser, and navigate to the Source URL."""
		i = self.Choice.GetSelection()
		url = self.source_urls[i].strip()
		if url:
			webbrowser.open(url)

	def edit_event(self, event):
		"""Open the default web browser, and navigate to the Edit Item Info page on BCScan.com."""
		webbrowser.open("http://www.bcscan.com/upcsubs.php?add&ref=%s&ean=%s" % (REF, self.ean))

	def goto_bcscan_event(self, event):
		"""Open the default web browser, and navigate to the BCScan Site."""
		webbrowser.open("http://www.bcscan.com")

	def goto_d4me_event(self, event):
		"""Open the default web browser, and navigate to the DirectionsForMe Site."""
		webbrowser.open("http://www.directionsforme.org")

	def exit_event(self, event):
		"""Exits the program."""
		self.Destroy()

	def about_event(self, event):
		"""Displays the about dialog."""
		self.notify("scrolled", "%s Version %s\nWritten by %s" % (APP_NAME, APP_VERSION, APP_AUTHOR), "About %s" % APP_NAME)

	def search_event(self, event):
		"""Starts a search in a new thread."""
		t = Thread(target=self._search)
		t.setDaemon(True)
		t.start()

	def _search(self):
		"""searches for an EAN on BCScan.com"""
		wx.CallAfter(self.InputArea.SetFocus)
		wx.CallAfter(self.LabelChoice.Disable)
		wx.CallAfter(self.Choice.Disable)
		wx.CallAfter(self.SourceButton.SetLabel, self.source_button_label)
		wx.CallAfter(self.SourceButton.Disable)
		wx.CallAfter(self.EditButton.Disable)
		wx.CallAfter(self.Choice.Clear)
		self.results = []
		self.source_names = []
		self.source_urls = []
		self.ean = ""
		wx.CallAfter(self.OutputArea.SetValue, "Searching...")
		wx.CallAfter(self.tts.silence)
		ean = self.InputArea.GetValue().strip()
		wx.CallAfter(self.InputArea.Clear)
		if not ean or len(ean)<6:
			return self.notify("error", "Invalid bar code!")
		params = {
			"ref": REF,
			"key": KEY,
			"token": TOKEN,
			"ean": ean,
		}
		if self.is_authorized:
			params["uid"] = self.uid
			params["pass"] = self.password
		req = Request(url="%slookup&%s" % (API_URL, urlencode(params)))
		req.add_header("User-Agent", AGENT)
		try:
			data = urlopen(req)
		except IOError as e:
			if hasattr(e, "reason"):
				msg = "\tServer is unreachable!\nMake sure you are connected to the internet."
			elif hasattr(e, "code"):
				msg = "The server couldn't fulfill the request. (Error "+str(e.code)+")"
			else:
				msg = "Unknown IO Error."
			return self.notify("error", msg)
		try:
			xml = ET.parse(data)
		except ET.ParseError:
			return self.notify("error", "Invalid XML feed.")
		data.close()
		err_msg = xml.findtext("./results/err_msg")
		if err_msg:
			return self.notify("error", err_msg)
		if self.is_authorized and not xml.findtext("./query/auth")=="1":
			self.is_authorized = False
			self.notify("information", "BCScan.com reports that your stored credentials are no longer valid.  This can happen if you've recently changed your password.  Please select 'logout' from the file menu, and then try logging in again.", "Warning: client no longer authorized.")
		self.ean = ean
		wx.CallAfter(self.EditButton.Enable)
		num_results = xml.findtext("./results/num_results")
		if num_results == "0":
			output = "Nothing found for that bar code."
			wx.CallAfter(self.OutputArea.SetValue, output)
			wx.CallAfter(self.tts.say, output)
			return
		names = []
		history_name = ""
		for result in xml.findall("./results/result"):
			details = []
			source_name = ""
			name = result.findtext("./name")
			name = "Unnamed" if not name else name
			if not history_name and name!="Unnamed":
				history_name = name
			if result.findtext("./type")=="private":
				name = name+" (private bar code)"
			for i in result.getchildren():
				tag = i.tag
				if tag=="type" or not i.text:
					continue
				elif tag == "source":
					source_name = i.text
				elif tag == "source_url":
					self.source_urls.append(i.text)
				elif tag=="name" and name:
					details.append(name)
				elif tag == "brand":
					details.append(i.text)
				elif len(tag+": "+i.text) < 80:
					details.append(tag.capitalize().replace("_", " ").strip()+": "+i.text)
				else:
					details.append(tag.capitalize().replace("_", " ").strip()+":\n"+i.text)
			self.results.append("\n".join(details)+"\n")
			self.source_names.append(source_name)
			if source_name:
				names.append("%s (From %s)" % (name, source_name.replace(" from Horizons for the Blind", "")))
			else:
				names.append("%s (From BCScan.com)" % name)
		wx.CallAfter(self.Choice.SetItems, names)
		wx.CallAfter(self.Choice.SetSelection, 0)
		if num_results != "1":
			wx.CallAfter(self.LabelChoice.Enable)
			wx.CallAfter(self.Choice.Enable)
			try:
				if CHOICE_SND:
					sound = wx.SoundFromData(CHOICE_SND)
					sound.Play(wx.SOUND_ASYNC)
			except NotImplementedError as e:
				pass
		if self.source_names[0] and self.source_urls[0]:
			wx.CallAfter(self.SourceButton.Enable)
			wx.CallAfter(self.SourceButton.SetLabel, self.source_button_label+" "+self.source_names[0])
		wx.CallAfter(self.OutputArea.SetValue, self.results[0])
		wx.CallAfter(self.tts.say, self.results[0])
		history_list = []
		count = 0
		for i in self.MenuHistory.GetMenuItems():
			i_id = i.GetId()
			i_name = i.GetText()
			i_ean = self.MenuHistory.GetHelpString(i_id)
			if i_name=="Empty..." or i_name=="Clear History" or count>=(MAX_HISTORY-1) or i_ean==ean:
				self.MenuHistory.DestroyId(i_id)
				continue
			history_list.append((i_ean, i_name))
			count += 1
		if not history_name:
			history_name = "Unnamed EAN (%s)" % ean
		history_list.insert(0, (ean, history_name))
		self.save_history(history_list)
		self.menu_bind(self.MenuHistory.Insert(0, wx.ID_ANY, history_name, ean), self.history_event)
		self.menu_bind(self.MenuHistory.Append(wx.ID_ANY, "Clear History", "Clears the history list."), self.clear_history_event)


app = wx.App(redirect=False)
window = MainFrame()
window.ShowFullScreen(True,wx.FULLSCREEN_NOTOOLBAR)
app.MainLoop()
