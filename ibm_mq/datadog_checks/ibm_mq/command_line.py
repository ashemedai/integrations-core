# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import re
import logging

from datadog_checks.utils.subprocess_output import get_subprocess_output

log = logging.getLogger(__file__)


class CommandLine:
    def __init__(self, config):
        self.config = config

        if self.config.docker_container:
            self.docker_container = self.config.docker_container
        else:
            self.docker_container = None

        self.cmd_path = os.path.join(self.config.mq_installation_dir, 'bin', 'runmqsc')
        self.queue_manager_name = self.config.queue_manager_name

    def _run_command(self, cmd):

        result, err, _ = get_subprocess_output(
            self._mk_cmd(cmd),
            log,
            False
        )

        return result, err

    def _mk_cmd(self, cmd):
        cmd = ['"'] + cmd + ['"']
        cmd = " ".join(cmd)

        cmd = ["echo", cmd]
        cmd.extend([
            "|",
            self.cmd_path,
            self.queue_manager_name
        ])

        full_cmd = [
            'bash',
            '-c',
            " ".join(cmd)
        ]

        return full_cmd

    def get_all_queues(self):
        cmd = ["dis", "queue('*')"]

        result, err = self._run_command(cmd)
        log.warning('hi')
        log.warning(err)
        if err:
            raise err

        log.warning(result)

        return result
