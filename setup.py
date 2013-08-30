# Copyright (c) 2013 Mikkel Schubert <MSchubert@snm.ku.dk>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#!/usr/bin/python
import os
import re
from distutils.core import setup


def locate_packages():
    packages = ['pypeline']
    for (dirpath, dirnames, _) in os.walk(packages[0]):
        for dirname in dirnames:
            package = os.path.join(dirpath, dirname).replace(os.sep, ".")
            packages.append(package)
    return packages


def locate_scripts():
    scripts = []
    for filename in os.listdir("bin"):
        if re.match(r"^[0-9a-z_]+", filename):
            script = os.path.join("bin", filename)
            if os.path.isfile(script) or os.path.islink(script):
                scripts.append(script)
    return scripts


setup(name         = 'Pypeline',
      version      = '0.1-dev',
      description  = '(Framework for) Bioinformatics pipelines',
      author       = 'Mikkel Schubert',
      author_email = 'MSchubert@snm.ku.dk',
      url          = 'https://github.com/MikkelSchubert/pypeline',
      requires     = ['pysam (>=0.7.4)',
                      'yaml (>=3.1.0)'],
      packages     = locate_packages(),
      scripts      = locate_scripts(),
    )