#!/usr/bin/env python3

"""
(1) Please refer to your ECU specifications, it is usually a call to UDS service RoutineControl (with a start command and the standardized "EraseMemory" routineId), but the parameters (a buffer of byte) are specific to your ECU:
UDS_SvcRoutineControl(CanHandle, msgReq, PUDS_SVC_PARAM_RC_STR, PUDS_SVC_PARAM_RC_RID_EM_, buffer, buffer_length);
(2) Your ECU will/should respond that it needs more time to process the request. It is a mechanims that is handled by UDS and ISO-TP communication protocols.

(3) Sending hex file is out of the scope of the UDS API, your process should include a way to convert hex file to binary (search for tools like hex2bin for example).
Sending content to an ECU is explained in UDS protocol (please check ISO-14229):
First you need to make a request to download data to your ECU using UDS_SvcRequestDownload.
Then in a loop, make UDS requests to transfer data with UDS_SvcTransferData until all the data are sent (the maximum size of the chunks of data is part of the response to the UDS service RequestDownload).
Finally complete the transfer with UDS_SvcRequestTransferExit.
"""

import struct
import traceback
from typing import Any

import time
import argparse
import cereal.messaging as messaging

from tqdm import tqdm

import panda.python.uds as uds
from cereal import car
from selfdrive.car.fingerprints import FW_VERSIONS, get_attr_from_cars
from selfdrive.car.isotp_parallel_query import IsoTpParallelQuery
from selfdrive.car.toyota.values import CAR as TOYOTA
from selfdrive.swaglog import cloudlog

Ecu = car.CarParams.Ecu

logcan = messaging.sub_sock('can')
sendcan = messaging.pub_sock('sendcan')

# TODO write best guess of read camera ecu memory
# sniff techstream

TESTER_PRESENT_REQUEST = bytes([uds.SERVICE_TYPE.TESTER_PRESENT, 0x0])
TESTER_PRESENT_RESPONSE = bytes([uds.SERVICE_TYPE.TESTER_PRESENT + 0x40, 0x0])

DEFAULT_DIAGNOSTIC_REQUEST = bytes([uds.SERVICE_TYPE.DIAGNOSTIC_SESSION_CONTROL,
                                    uds.SESSION_TYPE.DEFAULT])
DEFAULT_DIAGNOSTIC_RESPONSE = bytes([uds.SERVICE_TYPE.DIAGNOSTIC_SESSION_CONTROL + 0x40,
                                    uds.SESSION_TYPE.DEFAULT, 0x0, 0x32, 0x1, 0xf4])

EXTENDED_DIAGNOSTIC_REQUEST = bytes([uds.SERVICE_TYPE.DIAGNOSTIC_SESSION_CONTROL,
                                     uds.SESSION_TYPE.EXTENDED_DIAGNOSTIC])
EXTENDED_DIAGNOSTIC_RESPONSE = bytes([uds.SERVICE_TYPE.DIAGNOSTIC_SESSION_CONTROL + 0x40,
                                      uds.SESSION_TYPE.EXTENDED_DIAGNOSTIC, 0x0, 0x32, 0x1, 0xf4])



init = [
  [TESTER_PRESENT_REQUEST, DEFAULT_DIAGNOSTIC_REQUEST, EXTENDED_DIAGNOSTIC_REQUEST],
  [TESTER_PRESENT_RESPONSE, DEFAULT_DIAGNOSTIC_RESPONSE, EXTENDED_DIAGNOSTIC_RESPONSE]
]

query = IsoTpParallelQuery(sendcan, logcan, 1, (1872, 109), init[0], init[1], debug=True)
print(query.get_data(0.2))
# uds.SERVICE_TYPE.REQUEST_UPLOAD
# uds.SERVICE_TYPE.TRANSFER_DATA
# uds.SERVICE_TYPE.REQUEST_TRANSFER_EXIT
