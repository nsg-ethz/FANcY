import socket
import os
import errno
import struct
import sys
import traceback
import time
import subprocess

try:
    # python3
    from queue import Queue
except:
    # python2
    from Queue import Queue

from threading import Thread

try:
    # python2
    import cPickle as pickle
except:
    # python3
    import pickle


class KThread(Thread):
    """A subclass of threading.Thread, with a kill()
  method."""

    def __init__(self, *args, **keywords):
        Thread.__init__(self, *args, **keywords)
        self.killed = False

    def start(self):
        """Start the thread."""
        self.__run_backup = self.run
        self.run = self.__run  # Force the Thread to install our trace.
        Thread.start(self)

    def __run(self):
        """Hacked run function, which installs the
    trace."""
        sys.settrace(self.globaltrace)
        self.__run_backup()
        self.run = self.__run_backup

    def globaltrace(self, frame, why, arg):
        if why == 'call':
            return self.localtrace
        else:
            return None

    def localtrace(self, frame, why, arg):
        if self.killed:
            if why == 'line':
                raise SystemExit()
        return self.localtrace

    def kill(self):
        self.killed = True

# Helpers to send big packets


def send_msg(sock, msg):
    msg = struct.pack('>I', len(msg)) + msg
    sock.sendall(msg)


def recv_msg(sock):
    # Read message length and unpack it into an integer
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    # Read the message data
    return recvall(sock, msglen)


def recvall(sock, n):
    # Helper function to recv n bytes or return None if EOF is hit
    data = ''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None

        data += packet
    return data


class ClientTCP(object):
    def __init__(self, server_address=("localhost", 3007)):

        self.address = server_address
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # if its empty it means that we are not connected to anything
        self.connected_server = ()

    def createSocket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def close(self):

        self.connected_server = ()
        self.sock.close()

    def connect(self, server=()):

        if not self.connected_server:
            self.close()
            self.createSocket()
            if not server:
                self.sock.connect(self.address)
                self.connected_server = self.address
            else:
                self.sock.connect(server)
                self.connected_server = server

        elif self.connected_server != server:
            self.close()
            self.connect(server)

    def send(self, msg, server=()):

        reconnections = 3
        while reconnections:
            try:
                # creates socket and connects if necessary
                self.connect(server)
                send_msg(self.sock, pickle.dumps(msg))
                # breaks the while
                break

            except socket.error as serr:
                reconnections -= 1
                self.connected_server = ()
                if serr.errno != errno.ECONNREFUSED and serr.errno != errno.EPIPE and serr.errno != errno.ENOENT:
                    raise serr
                else:
                    print(serr)
                    print("Server {1}{0} could not be reached. Trying again...".format(
                        server, self.address))

        if not reconnections:
            raise socket.error

    def sendAndClose(self, msg, server):

        self.send(msg, server)
        time.sleep(0.1)
        self.close()


class ServerTCP(object):
    def __init__(self, address=(("localhost", 5000)), force=False, queue=None):

        self.address = address
        self.conn_handlers = {}
        self.conn_id = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        try:
            self.sock.bind(self.address)
        except:
            print(traceback.print_exc())
            if force:
                os.system("fuser -k %s/tcp" % address[1])
                self.sock.bind(self.address)
            else:
                print("Binding failed. Try again with force")

        self.sock.listen(200)

        # creates and returns queue if nothing
        if not queue:
            self.queue = Queue(0)
        else:
            self.queue = queue

    def get_queue(self):
        return self.queue

    def close(self):

        [conn[0].close() for conn in self.conn_handlers.values()]
        [thread[1].kill() for thread in self.conn_handlers.values()]
        self.conn_handlers = {}

        self.run_thread.kill()
        self.sock.close()

    def handleConnection(self, conn, queue, id):
        message = recv_msg(conn)
        while message:
            queue.put(pickle.loads(message))
            message = recv_msg(conn)

        if id in self.conn_handlers:
            del(self.conn_handlers[id])
        conn.close()

    def receive(self):
        return self.sock.recv(1024)

    def runThread(self):

        p = KThread(target=self.run)
        p.setDaemon(True)
        p.start()

        self.run_thread = p

    def run(self):

        try:
            while True:
                conn, addr = self.sock.accept()
                p = KThread(
                    target=self.handleConnection,
                    args=(conn, self.queue, self.conn_id))
                p.setDaemon(True)
                p.start()

                self.conn_handlers[self.conn_id] = [conn, p]
                self.conn_id += 1

        except:
            self.close()


# how to run the server
class CommandServer(object):

    def __init__(self, listen_port=3007):
        # listening port
        self.listen_port = listen_port
        self.server_queue = None

    def start(self):
        self.server = ServerTCP(
            ('', self.listen_port),
            force=False, queue=self.server_queue)
        self.server_queue = self.server.get_queue()
        self.server.runThread()

    def check_if_whitelisted(self, cmd, accepted_cmds):
        if any([cmd.startswith(x) for x in accepted_cmds]):
            return True
        return False

    def run(self):
        # reset pool
        self.start()

        while True:
            event = self.server_queue.get(timeout=365 * 24 * 60)
            self.server_queue.task_done()

            if "bash_cmd" in event:
                # filter bash commands with a whitelist
                cmd = event["bash_cmd"]
                if self.check_if_whitelisted(
                        cmd, ["mkdir", "killall iperf", "iperf"]):
                    print(event["bash_cmd"])
                    subprocess.Popen(event["bash_cmd"], shell=True)
                else:
                    print("Command blacklisted")
                    print(cmd)
            else:
                print("Invalid command type")


class TofinoCommandServer(object):

    def __init__(self, listen_port=3007, controller=None):
        # listening port
        self.listen_port = listen_port
        self.server_queue = None

        self.controller = controller

    def start(self):
        self.server = ServerTCP(
            ('', self.listen_port),
            force=False, queue=self.server_queue)
        self.server_queue = self.server.get_queue()
        self.server.runThread()

    def run(self):
        # reset pool
        self.start()

        while True:
            event = self.server_queue.get(timeout=365 * 24 * 60)
            self.server_queue.task_done()

            # only allow controller comands
            if "controller_cmd" in event:
                cmd = event["controller_cmd"]
                print(cmd)
                exec(cmd)
            else:
                print("Invalid command type")

#  client.send({"type": "terminate"}, src)
