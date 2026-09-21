from fastapi import FastAPI
from pydantic import BaseModel
import paramiko
import socket
import time


app = FastAPI()


USERNAME = "admin"
PASSWORD = "cisco"
SSH_PORT = 22


class ExecuteRequest(BaseModel):
    router_ip: str
    command: str


@app.get("/health")
def health():
    return {"status": "OK"}


@app.post("/execute")
def execute_command(request: ExecuteRequest):

    router_ip = request.router_ip.strip()
    command = request.command.strip()

    transport = None
    channel = None

    try:
        # ---------------------------------------------------------
        # Connect to router TCP port 22
        # ---------------------------------------------------------
        sock = socket.create_connection(
            (router_ip, SSH_PORT),
            timeout=15
        )

        # ---------------------------------------------------------
        # Create SSH transport
        # ---------------------------------------------------------
        transport = paramiko.Transport(sock)

        security_options = transport.get_security_options()

        # ---------------------------------------------------------
        # OLD CISCO IOS KEX
        # ---------------------------------------------------------
        supported_kex = set(security_options.kex)

        legacy_kex = [
            "diffie-hellman-group14-sha1",
            "diffie-hellman-group-exchange-sha1",
            "diffie-hellman-group1-sha1",
        ]

        usable_kex = [
            algorithm
            for algorithm in legacy_kex
            if algorithm in supported_kex
        ]

        if not usable_kex:
            raise Exception(
                "Paramiko does not support any of the legacy Cisco KEX algorithms"
            )

        security_options.kex = usable_kex

        # ---------------------------------------------------------
        # OLD CISCO HOST KEY
        # ---------------------------------------------------------
        supported_keys = set(security_options.key_types)

        if "ssh-rsa" in supported_keys:
            security_options.key_types = ("ssh-rsa",)
        else:
            raise Exception(
                "Paramiko does not support ssh-rsa host keys"
            )

        # ---------------------------------------------------------
        # CIPHERS
        #
        # Only select ciphers that THIS Paramiko installation
        # actually supports.
        # ---------------------------------------------------------
        supported_ciphers = set(security_options.ciphers)

        preferred_ciphers = [
            "aes128-ctr",
            "aes192-ctr",
            "aes256-ctr",
            "aes128-cbc",
            "3des-cbc",
        ]

        usable_ciphers = [
            cipher
            for cipher in preferred_ciphers
            if cipher in supported_ciphers
        ]

        if not usable_ciphers:
            raise Exception(
                "No compatible SSH cipher is available"
            )

        security_options.ciphers = usable_ciphers

        # ---------------------------------------------------------
        # Start SSH client
        # ---------------------------------------------------------
        transport.start_client(timeout=15)

        # ---------------------------------------------------------
        # Password authentication
        # ---------------------------------------------------------
        transport.auth_password(
            username=USERNAME,
            password=PASSWORD
        )

        if not transport.is_authenticated():
            raise Exception("SSH authentication failed")

        # ---------------------------------------------------------
        # Interactive shell
        # ---------------------------------------------------------
        channel = transport.open_session()

        channel.get_pty()

        channel.invoke_shell()

        time.sleep(1)

        # Clear initial Cisco banner/prompt
        if channel.recv_ready():
            channel.recv(65535)

        # ---------------------------------------------------------
        # Send command
        # ---------------------------------------------------------
        channel.send(command + "\n")

        time.sleep(2)

        # ---------------------------------------------------------
        # Receive output
        # ---------------------------------------------------------
        output = ""

        while channel.recv_ready():
            output += channel.recv(65535).decode(
                "utf-8",
                errors="ignore"
            )

        return {
            "success": True,
            "router_ip": router_ip,
            "command": command,
            "output": output
        }

    except socket.timeout:
        return {
            "success": False,
            "router_ip": router_ip,
            "error": "Connection to router timed out"
        }

    except ConnectionRefusedError:
        return {
            "success": False,
            "router_ip": router_ip,
            "error": "Connection refused. Check that SSH is enabled on the router."
        }

    except Exception as e:
        return {
            "success": False,
            "router_ip": router_ip,
            "error": str(e)
        }

    finally:

        if channel is not None:
            try:
                channel.close()
            except Exception:
                pass

        if transport is not None:
            try:
                transport.close()
            except Exception:
                pass
