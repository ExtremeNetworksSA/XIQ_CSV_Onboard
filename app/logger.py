#!/usr/bin/env python3
import logging
import os
import time
import inspect
current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)

PATH = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
	filename='{}/xiq_serial_onboard.log'.format(parent_dir),
	filemode='a',
	level=os.environ.get("LOGLEVEL", "INFO"),
	format= '{}: %(name)s - %(levelname)s - %(message)s'.format(time.strftime("%Y-%m-%d %H:%M"))
)

logger = logging.getLogger("Serial_Onboard")