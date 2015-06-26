# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import glob
import os
import shutil
import sys
import zlib
from distutils.core import setup

import py2exe

from constants import APP_NAME, APP_VERSION, APP_AUTHOR

# ModuleFinder can't handle runtime changes to __path__, but win32com uses them
try:
	# py2exe 0.6.4 introduced a replacement modulefinder.
	# This means we have to add package paths there, not to the built-in one.
	# If this new modulefinder gets integrated into Python, then we might be able to revert this some day.
	# if this doesn't work, try import modulefinder
	try:
		import py2exe.mf as modulefinder
	except ImportError:
		import modulefinder
	import win32com, sys
	for p in win32com.__path__[1:]:
		modulefinder.AddPackagePath("win32com", p)
	for extra in ["win32com.shell"]:
		__import__(extra)
		m = sys.modules[extra]
		for p in m.__path__[1:]:
			modulefinder.AddPackagePath(extra, p)
except ImportError:
	pass


# Remove the build folder if it exists.
shutil.rmtree("build", ignore_errors=True)
# do the same for dist folder if it exists.
shutil.rmtree("dist", ignore_errors=True)

# If run without args, build executables, in quiet mode.
if len(sys.argv) == 1:
	sys.argv.append("py2exe")
	sys.argv.append("-q")


class Target(object):
	def __init__(self, **kw):
		self.__dict__.update(kw)
		# for the versioninfo resources
		self.version = APP_VERSION
		self.company_name = ""
		self.copyright = APP_AUTHOR
		self.name = APP_NAME


# The manifest will be inserted as a resource into the executable. This gives the controls the Windows XP appearance (if run on XP ;-)
manifest_template = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
<assemblyIdentity
	version="5.0.0.0"
	processorArchitecture="x86"
	name="%(prog)s"
	type="win32"
/>
<description>%(prog)s Program</description>
<trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
	<security>
		<requestedPrivileges>
			<requestedExecutionLevel
				level="asInvoker"
				uiAccess="false">
			</requestedExecutionLevel>
		</requestedPrivileges>
	</security>
</trustInfo>
<dependency>
	<dependentAssembly>
		<assemblyIdentity
			type="win32"
			name="Microsoft.VC90.CRT"
			version="9.0.21022.8"
			processorArchitecture="x86"
			publicKeyToken="1fc8b3b9a1e18e3b">
		</assemblyIdentity>
	</dependentAssembly>
</dependency>
<dependency>
	<dependentAssembly>
		<assemblyIdentity
			type="win32"
			name="Microsoft.Windows.Common-Controls"
			version="6.0.0.0"
			processorArchitecture="X86"
			publicKeyToken="6595b64144ccf1df"
			language="*"
		/>
	</dependentAssembly>
</dependency>
</assembly>
"""

RT_MANIFEST = 24

program = Target(
	# used for the versioninfo resource
	description = "%s V%s" % (APP_NAME, APP_VERSION),
	# what to build
	script = "%s.pyw" % APP_NAME,
	other_resources = [(RT_MANIFEST, 1, manifest_template % dict(prog=APP_NAME))],
	icon_resources = [(1, "%s.ico" % APP_NAME)],
	dest_base = APP_NAME
)


excludes = [
	"_ssl",
	"_gtkagg",
	"_tkagg",
	"bsddb",
	"curses",
	"email",
	"pywin.debugger",
	"pywin.debugger.dbgcon",
	"pywin.dialogs",
	"tcl",
	"Tkconstants",
	"Tkinter",
	"pdbunittest",
	"difflib",
	"pyreadline",
	"optparse",
	"pickle",
	"calendar",
]


packages = [
	"xml.etree",
	"json",
	"encodings.utf_8",
	"encodings.ascii",
	"encodings.latin_1",
	"encodings.hex_codec"
]


dll_excludes = [
	"libgdk-win32-2.0-0.dll",
	"libgobject-2.0-0.dll",
	"tcl84.dll",
	"tk84.dll",
	"MSVCP90.dll",
	"mswsock.dll",
	"powrprof.dll",
	"python23.dll",
	"_sre.pyd",
	"_winreg.pyd",
	"unicodedata.pyd",
	"zlib.pyd",
	"wxc.pyd",
	"wxmsw24uh.dll",
	"w9xpopen.exe",
]


setup(
	options = {
		"py2exe": {
			"bundle_files": True,
			"ascii": True,
			"compressed": True,
			"optimize": 2,
			"excludes": excludes,
			"packages": packages,
			"dll_excludes": dll_excludes,
		}
	},
	zipfile = None,
	windows = [program],
	data_files = [
		("sounds", glob.glob("sounds\\*")),
		("speech_libs", glob.glob("speech_libs\\*")),
	],
)

# Remove the build folder since we no longer need it.
shutil.rmtree("build", ignore_errors=True)
