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

import binascii
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

# REQUEST_UPLOAD_REQUEST = bytes([uds.SERVICE_TYPE.REQUEST_UPLOAD, 0x0, ])

init = [
  [TESTER_PRESENT_REQUEST, DEFAULT_DIAGNOSTIC_REQUEST, EXTENDED_DIAGNOSTIC_REQUEST],
  [TESTER_PRESENT_RESPONSE, DEFAULT_DIAGNOSTIC_RESPONSE, EXTENDED_DIAGNOSTIC_RESPONSE]
]

query = IsoTpParallelQuery(sendcan, logcan, 1, (1872, 109), init[0], init[1], debug=True)
print(query.get_data(0.2))

def request_upload(memory_address: int, memory_size: int, memory_address_bytes: int = 4, memory_size_bytes: int = 4, data_format: int = 0x00):
  data = bytes([data_format])

  if memory_address_bytes < 1 or memory_address_bytes > 4:
    raise ValueError('invalid memory_address_bytes: {}'.format(memory_address_bytes))
  if memory_size_bytes < 1 or memory_size_bytes > 4:
    raise ValueError('invalid memory_size_bytes: {}'.format(memory_size_bytes))
  data += bytes([memory_size_bytes << 4 | memory_address_bytes])

  if memory_address >= 1 << (memory_address_bytes * 8):
    raise ValueError('invalid memory_address: {}'.format(memory_address))
  data += struct.pack('!I', memory_address)[4 - memory_address_bytes:]
  if memory_size >= 1 << (memory_size_bytes * 8):
    raise ValueError('invalid memory_size: {}'.format(memory_size))
  data += struct.pack('!I', memory_size)[4 - memory_size_bytes:]

  requp = [
    bytes([uds.SERVICE_TYPE.REQUEST_UPLOAD]) + data,
    bytes([uds.SERVICE_TYPE.REQUEST_UPLOAD + 0x40])
  ]
  q = IsoTpParallelQuery(sendcan, logcan, 1, (1872, 109), requp[0], requp[1], debug=True)
  resp = query.get_data()
  print(resp)
  for k, v in resp.items():
    print(binascii.hexlify(v))
  return resp

request_upload(0x0, 0xFFFF)
#   # max_num_bytes_len = resp[0] >> 4 if len(resp) > 0 else 0
#   # if max_num_bytes_len >= 1 and max_num_bytes_len <= 4:
#   #   max_num_bytes = struct.unpack('!I', (b"\x00" * (4 - max_num_bytes_len)) + resp[1:max_num_bytes_len + 1])[0]
#   # else:
#   #   raise ValueError('invalid max_num_bytes_len: {}'.format(max_num_bytes_len))

#   # return max_num_bytes  # max number of bytes per transfer data request

# requp = [
#   []
# ]
# query = IsoTpParallelQuery(sendcan, logcan, 1, (1872, 109), init[0], init[1], debug=True)
# print(query.get_data(0.2))

# uds.SERVICE_TYPE.REQUEST_UPLOAD
# uds.SERVICE_TYPE.TRANSFER_DATA
# uds.SERVICE_TYPE.REQUEST_TRANSFER_EXIT
