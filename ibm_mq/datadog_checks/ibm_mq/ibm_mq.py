# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import division

from datadog_checks.checks import AgentCheck

from six import iteritems

from . import errors
from .metrics import Metrics
from .config import IBMMQConfig
from .connection import Connection
from .environment import Environment
from .command_line import CommandLine


class IbmMqCheck(AgentCheck):

    METRIC_PREFIX = 'ibm_mq'

    SERVICE_CHECK = 'ibm_mq.can_connect'

    QUEUE_MANAGER_SERVICE_CHECK = 'ibm_mq.queue_manager'
    QUEUE_SERVICE_CHECK = 'ibm_mq.queue'

    def check(self, instance):
        config = IBMMQConfig(instance)
        environment = Environment(config)
        config.check_properly_configured()
        environment.set_env()

        try:
            import pymqi
            self.pymqi = pymqi
        except ImportError as e:
            self.log.error("You need to install pymqi: {}".format(e))
            raise errors.PymqiException("You need to install pymqi: {}".format(e))

        metrics = Metrics()

        try:
            conn = Connection()
            queue_manager = conn.get_queue_manager_connection(config)
            self.service_check(self.SERVICE_CHECK, AgentCheck.OK, config.tags)
        except Exception as e:
            self.warning("cannot connect to queue manager: {}".format(e))
            self.service_check(self.SERVICE_CHECK, AgentCheck.CRITICAL, config.tags)
            environment.clean_env()
            return

        self.queue_manager_stats(queue_manager, config.tags, metrics)
        self.channel_stats(queue_manager, config.tags, metrics)

        cli = CommandLine(config)

        queues = cli.get_all_queues()
        self.log.warning('test')
        self.log.warning(queues)

        for queue_name in config.queues:
            queue_tags = config.tags + ["queue:{}".format(queue_name)]
            try:
                queue = self.pymqi.Queue(queue_manager, queue_name)
                self.queue_stats(queue, queue_tags, metrics)
                self.service_check(self.QUEUE_SERVICE_CHECK, AgentCheck.OK, queue_tags)
                queue.close()
            except Exception as e:
                self.warning('Cannot connect to queue {}: {}'.format(queue_name, e))
                self.service_check(self.QUEUE_SERVICE_CHECK, AgentCheck.CRITICAL, queue_tags)

        environment.clean_env()
        queue_manager.disconnect()

    def queue_manager_stats(self, queue_manager, tags, metrics):
        for mname, pymqi_value in iteritems(metrics.queue_manager_metrics()):
            try:
                m = queue_manager.inquire(pymqi_value)

                mname = '{}.queue_manager.{}'.format(self.METRIC_PREFIX, mname)
                self.gauge(mname, m, tags=tags)
                self.service_check(self.QUEUE_MANAGER_SERVICE_CHECK, AgentCheck.OK, tags)
            except self.pymqi.Error as e:
                self.warning("Error getting queue manager stats: {}".format(e))
                self.service_check(self.QUEUE_MANAGER_SERVICE_CHECK, AgentCheck.CRITICAL, tags)

    def queue_stats(self, queue, tags, metrics):
        for mname, pymqi_value in iteritems(metrics.queue_metrics()):
            try:
                m = queue.inquire(pymqi_value)
                mname = '{}.queue.{}'.format(self.METRIC_PREFIX, mname)
                self.log.debug("name={} value={} tags={}".format(mname, m, tags))
                self.gauge(mname, m, tags=tags)
            except self.pymqi.Error as e:
                self.warning("Error getting queue stats: {}".format(e))

        for mname, func in iteritems(metrics.queue_metrics_functions()):
            try:
                m = func(queue)
                mname = '{}.queue.{}'.format(self.METRIC_PREFIX, mname)
                self.log.debug("name={} value={} tags={}".format(mname, m, tags))
                self.gauge(mname, m, tags=tags)
            except self.pymqi.Error as e:
                self.warning("Error getting queue stats: {}".format(e))

    def channel_stats(self, queue_manager, tags, metrics):
        for mname, pymqi_value in iteritems(metrics.channel_metrics()):
            try:
                m = queue_manager.inquire(pymqi_value)
                mname = '{}.channel.{}'.format(self.METRIC_PREFIX, mname)
                self.log.debug("name={} value={} tags={}".format(mname, m, tags))
                self.gauge(mname, m, tags=tags)
            except self.pymqi.Error as e:
                self.warning("Error getting channel stats: {}".format(e))
