"""Reliable lifecycle for WiiM Home's fixed-port UPnP observer server."""
import errno
import threading


def _transport_summary(message):
    if not isinstance(message, dict):
        return {}
    keys = ("playState", "duration", "progress", "lastPlayIndex", "trackId")
    summary = {key: message[key] for key in keys if key in message}
    if message.get("playUri"):
        summary["hasTrackUri"] = True
    return summary


def install_observer_lifecycle_fix():
    from LPClientFramework import LPUPnPObserverManager as module

    manager_class = module.LPUPnPObserverManager
    if getattr(manager_class, "_linux_observer_lifecycle_fix_installed", False):
        return

    if hasattr(manager_class, "_maintainSubscriptions"):
        # 0.2.10 has native generation-aware renewals and clean shutdown.
        # Keep that lifecycle intact; only hand it the pre-reserved socket.
        original_server = module.LPThreadHTTPServer

        class ReservedObserverServer(original_server):
            def __init__(self, address, handler, bind_and_activate=True):
                from single_instance import take_observer_reservation
                reservation = take_observer_reservation(address[1]) if bind_and_activate else None
                if reservation is None:
                    super().__init__(address, handler, bind_and_activate=bind_and_activate)
                    return
                try:
                    super().__init__(address, handler, bind_and_activate=False)
                    self.socket.close()
                    self.socket = reservation
                    self.server_address = reservation.getsockname()
                    self.server_activate()
                except BaseException:
                    reservation.close()
                    raise
                module.logger.info("[UPnP observer] adopted startup reservation on 0.0.0.0:%d", address[1])

        module.LPThreadHTTPServer = ReservedObserverServer
        manager_class._linux_observer_lifecycle_fix_installed = True
        return

    original_stop = manager_class.stop

    def start(self):
        existing = getattr(self, "httpServer", None)
        existing_thread = getattr(self, "serverThread", None)
        if existing is not None or (existing_thread is not None and existing_thread.is_alive()):
            module.logger.debug("[UPnP observer] start ignored; server is already active")
            return True

        handler = module.partial(module.LPSimpleUPnPObserverHandler, self.messageDistributeMethod)
        try:
            from single_instance import take_observer_reservation
            reservation = take_observer_reservation(self.port)
            if reservation is None:
                server = module.LPThreadHTTPServer(("", self.port), handler)
            else:
                server = module.LPThreadHTTPServer(("", self.port), handler, bind_and_activate=False)
                unbound_socket = server.socket
                server.socket = reservation
                unbound_socket.close()
                server.server_address = reservation.getsockname()
                server.server_activate()
                module.logger.info("[UPnP observer] adopted startup reservation on 0.0.0.0:%d", self.port)
        except OSError as error:
            self.serverSwitch = False
            self.observerBindError = error
            if error.errno == errno.EADDRINUSE:
                module.logger.error(
                    "[UPnP observer] fixed listener 0.0.0.0:%d is occupied; "
                    "another WiiM Home instance or local service owns it", self.port,
                )
                return False
            raise

        self.serverSwitch = True
        self.observerBindError = None
        self.httpServer = server
        if not getattr(self, "_linux_transport_callback_wrapped", False):
            original_callback = self.notifyComeMethod

            def transport_callback(uuid, message):
                summary = _transport_summary(message)
                if summary:
                    module.logger.info(
                        "[UPnP transport] parsed callback device=%s fields=%s", uuid, summary,
                    )
                return original_callback(uuid, message)

            self.notifyComeMethod = transport_callback
            self._linux_transport_callback_wrapped = True

        def serve():
            module.logger.info("Start UPnP observer service on 0.0.0.0:%d", self.port)
            try:
                server.serve_forever()
            finally:
                server.server_close()

        self.serverThread = threading.Thread(target=serve, name="UPnPObserverServerThread", daemon=True)
        self.serverThread.start()

        # Preserve the original subscription timeout/resubscribe worker.  Its
        # original start method is only needed for this worker, but it also
        # binds the HTTP server, so run an equivalent bounded daemon loop.
        def timeout_loop():
            while self.serverSwitch:
                for _ in range(60):
                    if not self.serverSwitch:
                        return
                    threading.Event().wait(1)
                with self.observerDictLock:
                    expired = [
                        value for value in self.observerDict.values()
                        if (module.datetime.datetime.now() - value["timestamp"]).total_seconds()
                        > value["timeout"] / 2
                    ]
                for value in expired:
                    def resubscribe(entry=value):
                        with self.observerDictLock:
                            self.observerDict.pop(entry["sid"], None)
                        result = self.subscribe(entry["ip"], entry["port"], entry["service"], entry["uuid"])
                        if result:
                            with self.observerDictLock:
                                self.observerDict.update(result)
                    threading.Thread(target=resubscribe, name="UPnPObserverResubscribe", daemon=True).start()

        self.timeoutThread = threading.Thread(target=timeout_loop, name="UPnPObserverTimeoutThread", daemon=True)
        self.timeoutThread.start()
        return True

    def stop(self):
        server_thread = getattr(self, "serverThread", None)
        original_stop(self)
        if server_thread is not None and server_thread is not threading.current_thread():
            server_thread.join(timeout=2)
        self.serverThread = None

    manager_class.start = start
    manager_class.stop = stop

    manager_class._linux_observer_lifecycle_fix_installed = True
