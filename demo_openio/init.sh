cd enoss

curl https://bootstrap.pypa.io/pip/2.7/get-pip.py --output get-pip.py
python2 get-pip.py
pip2 install -r requirements-py2.txt

pip3 install -U setuptools
pip3 install wheel
python3 setup.py sdist bdist_wheel

pip2 install dist/*whl

pip3 install greenstalk
