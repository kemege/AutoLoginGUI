# -*- encoding: utf-8 -*-
import os
# Disable GreenDNS before importing eventlet
# to avoid incompatibility with pyinstaller
os.environ['EVENTLET_NO_GREENDNS'] = 'yes'
