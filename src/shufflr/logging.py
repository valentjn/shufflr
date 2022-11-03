#!/usr/bin/python3
# Copyright (C) 2022 Julian Valentin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging


def SetUpLogger() -> None:
  handler = logging.StreamHandler()
  formatter = logging.Formatter("%(message)s")
  handler.setFormatter(formatter)
  gLogger.addHandler(handler)


gLogger = logging.Logger("shufflr")
SetUpLogger()
