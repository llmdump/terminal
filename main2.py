#!/usr/bin/env python
# OK first i need to get the logo
import json
import colorama
import math
colorama.init(autoreset=True)
print("Setting up server...")
start=(105, 120, 250)
end=(76, 200, 229)
def get_gradient(steps,n):

    ans=[0,0,0]
    t=n/(steps-1)
    ans[0]=math.floor((1-t)*start[0]+t*end[0])
    ans[1]=math.floor((1-t)*start[1]+t*end[1])
    ans[2]=math.floor((1-t)*start[2]+t*end[2])
    return f"\x1b[1;38;2;{ans[0]};{ans[1]};{ans[2]};49m"
llm_color="\x1b[1;38;2;193;198;220;49m"
pipe_color="\x1b[1;38;2;255;255;255;49m"
dump_color="\x1b[1;38;2;71;82;109;49m"
reset_color="\x1b[0;39;49m".encode()
starter_color="\x1b[0;38;2;76;200;229;49m".encode()
print("Loading logo.txt...")
with open("logo.txt") as f:
    raw_logo=f.read()
print("Loading logo.json...")
with open("logo.json") as f:
    sections=json.load(f).get("sections", [])
logo=""
for i in raw_logo.split("\n"):
    for index,j in enumerate(i):
        logo+=get_gradient(len(i),index)+j
    logo+="\r\n"+reset_color.decode()

print(logo)
print("Starting server...")

# define some functions for AI stuff
def chat_ai(messages:list[dict]): #[{"role": "user", "content": "Tell me a joke!"}]
    url = "https://ai.hackclub.com/chat/completions"
    headers = {"Content-Type": "application/json"}
    data = {"messages": messages,"model":"openai/gpt-oss-120b"}

    
    response:requests.Response = requests.post(url, headers=headers, json=data)
    res_text = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    print(res_text)
    # Replace tags with colorama codes
    color_map = {
        "[c]": colorama.Fore.BLUE,
        "[blue]": colorama.Fore.BLUE,
        "[red]": colorama.Fore.RED,
        "[green]": colorama.Fore.GREEN,
        "[yellow]": colorama.Fore.YELLOW,
        "[magenta]": colorama.Fore.MAGENTA,
        "[cyan]": colorama.Fore.CYAN,
        "[white]": colorama.Fore.WHITE,
        "[black]": colorama.Fore.BLACK,
    }
    for tag, color in color_map.items():
        res_text = res_text.replace(tag, color)
    res_text = res_text.replace("[b]", colorama.Style.BRIGHT).replace("[r]", colorama.Style.RESET_ALL)
    res_text = res_text.replace("\n", "\r\n") + "\r\n"
    res_text = res_text.encode('utf-8')
    msgs=messages+[{"role": "assistant", "content": response.json().get("choices", [{}])[0].get("message", {}).get("content", "")}]
    return res_text,msgs
    
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

import sys

from zope.interface import implementer

from twisted.conch import avatar
from twisted.conch.checkers import InMemorySSHKeyDB, SSHPublicKeyChecker
from twisted.conch.ssh import connection, factory, keys, session, userauth
from twisted.conch.ssh.transport import SSHServerTransport
from twisted.cred import portal
from twisted.cred.checkers import InMemoryUsernamePasswordDatabaseDontUse, ICredentialsChecker
from twisted.cred import credentials
from twisted.internet import defer
from twisted.internet import protocol, reactor
from twisted.python import components, log
import requests

log.startLogging(sys.stderr)

"""
Example of running a custom protocol as a shell session over an SSH channel.

Warning! This implementation is here to help you understand how Conch SSH
server works. You should not use this code in production.

Re-using a private key is dangerous, generate one.

For this example you can use:

$ ckeygen -t rsa -f ssh-keys/ssh_host_rsa_key
$ ckeygen -t rsa -f ssh-keys/client_rsa

Re-using DH primes and having such a short primes list is dangerous, generate
your own primes.

In this example the implemented SSH server identifies itself using an RSA host
key and authenticates clients using username "user" and password "password" or
using a SSH RSA key.

# Clean the previous server key as we should now have a new one
$ ssh-keygen -f ~/.ssh/known_hosts -R [localhost]:5022
# Connect with password
$ ssh -p 5022 -i ssh-keys/client_rsa user@localhost
# Connect with the SSH client key.
$ ssh -p 5022 -i ssh-keys/client_rsa user@localhost
"""

# Path to RSA SSH keys used by the server.
SERVER_RSA_PRIVATE = "ssh-keys/ssh_host_rsa_key"
SERVER_RSA_PUBLIC = "ssh-keys/ssh_host_rsa_key.pub"

# Path to RSA SSH keys accepted by the server.
CLIENT_RSA_PUBLIC = "ssh-keys/client_rsa.pub"


# Pre-computed big prime numbers used in Diffie-Hellman Group Exchange as
# described in RFC4419.
# This is a short list with a single prime member and only for keys of size
# 1024 and 2048.
# You would need a list for each SSH key size that you plan to support in your
# server implementation.
# You can use OpenSSH ssh-keygen to generate these numbers.
# See the MODULI GENERATION section from the ssh-keygen man pages.
# See moduli man pages to find out more about the format used by the file
# generated using ssh-keygen.
# For Conch SSH server we only need the last 3 values:
# * size
# * generator
# * modulus
#
# The format required by the Conch SSH server is:
#
# {
#   size1: [(generator1, modulus1), (generator1, modulus2)],
#   size2: [(generator4, modulus3), (generator1, modulus4)],
# }
#
# twisted.conch.openssh_compat.primes.parseModuliFile provides a parser for
# reading OpenSSH moduli file.
#
# Warning! Don't use these numbers in production.
# Generate your own data.
# Avoid 1024 bit primes https://weakdh.org
#
PRIMES = {
    2048: [
        (
            2,
            int(
                "2426544657763384657581346888965894474823693600310397077868393"
                "3705240497295505367703330163384138799145013634794444597785054"
                "5748125479903006919561762337599059762229781976243372717454710"
                "2176446353691318838172478973705741394375893696394548769093992"
                "1001501857793275011598975080236860899147312097967655185795176"
                "0369411418341859232907692585123432987448282165305950904719704"
                "0150626897691190726414391069716616579597245962241027489028899"
                "9065530463691697692913935201628660686422182978481412651196163"
                "9303832327425472811802778094751292202887555413353357988371733"
                "1585493104019994344528544370824063974340739661083982041893657"
                "4217939"
            ),
        )
    ],
    4096: [
        (
            2,
            int(
                "8896338360072960666956554817320692705506152988585223623564629"
                "6621399423965037053201590845758609032962858914980344684974286"
                "2797136176274424808060302038380613106889959709419621954145635"
                "9745645498927756607640582597997083132103281857166287942205359"
                "2801914659358387079970048537106776322156933128608032240964629"
                "7706526831155237865417316423347898948704639476720848300063714"
                "8566690545913773564541481658565082079196378755098613844498856"
                "5501586550793900950277896827387976696265031832817503062386128"
                "5062331536562421699321671967257712201155508206384317725827233"
                "6142027687719225475523981798875719894413538627861634212487092"
                "7314303979577604977153889447845420392409945079600993777225912"
                "5621285287516787494652132525370682385152735699722849980820612"
                "3709076387834615230428138807577711774231925592999456202847308"
                "3393989687120016431260548916578950183006118751773893012324287"
                "3304901483476323853308396428713114053429620808491032573674192"
                "3854889258666071928702496194370274594569914312983133822049809"
                "8897129264121785413015683094180147494066773606688103698028652"
                "0892090232096545650051755799297658390763820738295370567143697"
                "6176702912637347103928738239565891710671678397388962498919556"
                "8943711148674858788771888256438487058313550933969509621845117"
                "4112035938859"
            ),
        )
    ],
}


@implementer(ICredentialsChecker)
class AcceptAnythingChecker:
    """
    A checker that accepts any username/password combination.
    """
    credentialInterfaces = (credentials.IUsernamePassword,)
    
    def requestAvatarId(self, credentials):
        """
        Accept any credentials and return the username as the avatar ID.
        """
        return defer.succeed(credentials.username)


class ExampleAvatar(avatar.ConchUser):
    """
    The avatar is used to configure SSH services/sessions/subsystems for
    an account.

    This account will use L{session.SSHSession} to handle a channel of
    type I{session}.
    """

    def __init__(self, username):
        avatar.ConchUser.__init__(self)
        self.username = username
        self.channelLookup.update({b"session": session.SSHSession})


@implementer(portal.IRealm)
class ExampleRealm:
    """
    When using Twisted Cred, the pluggable authentication framework, the
    C{requestAvatar} method should return a L{avatar.ConchUser} instance
    as required by the Conch SSH server.
    """

    def requestAvatar(self, avatarId, mind, *interfaces):
        """
        See: L{portal.IRealm.requestAvatar}
        """
        return interfaces[0], ExampleAvatar(avatarId), lambda: None


class EchoProtocol(protocol.Protocol):
    """
    This is our protocol that we will run over the shell session.
    """

    def __init__(self):
        self.buffer = b""
        self.greeted = False
        self.memory = [{"role":"system","content":"""You are LLM Dump, a helpful assistant.
Try keeping your responses concise, at around 400 characters, unless the user says otherwise, and don't use Markdown. 
Use the following syntax:
Type [b] to bold, [c] to highlight as blue, and [r] to reset.
Use the following syntax for other colors:
[red], [green], [yellow], [blue], [magenta], [cyan]
These are not HTML tags, so NEVER end them with [/c], [/b], [/red], etc. Close them with [r]. Example: 
[c]Artificial Intelligence (AI)[r] is a branch of computer science that creates systems capable of tasks that normally require human intelligence—such as learning, reasoning, problem-solving, perception, and language ...
For code snippets, type [Language code] at the start, replacing Language with the actual language name, and [End of code] at the end.
You will have to manually syntax highlight the code. Example:
[Python code]
[red]def [yellow]hello_world[blue]()[r]:
    [green]text_to_print[red]=[cyan]"Hello, world!"[r]
    [yellow]print[blue]([green]text_to_print[blue])[r]
    [magenta]# This prints hello world[r]
[End of code]
To syntax highlight, follow these general rules:
Keywords (def, return, if, else, import, etc.): [red]
Symbols and punctuation (-,=,+,<,>, and escape sequences): [red]
Strings: [cyan]
Function names: [yellow]
Variable names: [green]
Class names: [b][yellow] which bolds the text
Brackets and parentheses: [blue]
Comments: [magenta]
Reset all formatting after the code snippet with [r].

""" }]  # To store conversation history per user
    def connectionMade(self):
        """
        Called when the connection is established.
        """
        self.transport.write(logo.encode('utf-8'))
        self.transport.write(starter_color+b"Welcome to LLM Dump in the terminal!\r\n")
        self.transport.write(b"Type something and hit enter, or Ctrl+D or Ctrl+Z to exit.\r\n")
        self.transport.write(b"Type Ctrl+C to discard message and Ctrl+A to add newline.\r\n")
        self.transport.write(colorama.Fore.GREEN.encode()+b"Note: Since this uses Hackclub AI, your messages may be logged.\r\n")
        self.transport.write(b"Github: "+ colorama.Fore.CYAN.encode()+b"https://github.com/https://github.com/llmdump/terminal" + b"\r\n")
        self.transport.write(b"You may have to wait ~2-4 seconds after hitting Enter.\r\n\r\n"+reset_color)
        self.transport.write(starter_color+b"> ")
        self.greeted = True

    def dataReceived(self, data):
        """
        Called when client send data over the shell session.
        
        Collect input until newline, then echo it back with "you typed: " prefix.
        Exit on EOF (Ctrl+D) or Ctrl+C.
        """
        if data == b"\x04":  # ^D (EOF)
            self.transport.write(reset_color)
            self.transport.write(b"\r\nExiting...\r\n")
            self.transport.loseConnection()
            return
        elif data == b"\x03":  # ^C
            self.transport.write(reset_color)
            self.transport.write(b"\r\n")
            self.buffer = b""
            self.transport.write(b"Press Ctrl+D or Ctrl+Z to exit.\r\n")
            self.transport.write(starter_color+b"> ")
            return
        elif data == b"\x01": # ^A (add newline)
            self.buffer += b"\n"
            self.transport.write(b"\r\n")
            self.transport.write(starter_color+b"..") #Indicate continuation
            return
        elif data == b"\x1a":  # ^Z (also treated as EOF in some contexts)
            self.transport.write(reset_color)
            self.transport.write(b"\r\nExiting...\r\n")
            self.transport.loseConnection()
            return
        elif data == b"\r" or data == b"\n":
            # User pressed enter
            self.transport.write(b"\r\n")
            self.transport.write(reset_color)
            if self.buffer:
                # response = b"\r\nyou typed: " + self.buffer + b"\r\n"
                self.memory.append({"role":"user","content":self.buffer.decode()})
                response,self.memory=chat_ai(self.memory)
                self.transport.write(response)
                self.buffer = b""
                self.transport.write(b"\r\n")
            else:
                self.transport.write(b"\r\n")
            self.transport.write(starter_color+b"> ")
        elif data == b"\x7f" or data == b"\x08":  # Backspace or DEL
            if self.buffer:
                self.buffer = self.buffer[:-1]
                # Send backspace sequence to terminal
                self.transport.write(b"\x08 \x08")
        elif data.decode().isprintable():
            # Regular character - add to buffer and echo
            self.buffer += data
            self.transport.write(data)
        else:
            # Ignore other control characters
            pass


@implementer(session.ISession, session.ISessionSetEnv)
class ExampleSession:
    """
    This selects what to do for each type of session which is requested by the
    client via the SSH channel of type I{session}.
    """

    def __init__(self, avatar):
        """
        In this example the avatar argument is not used for session selection,
        but for example you can use it to limit I{shell} or I{exec} access
        only to specific accounts.
        """

    def getPty(self, term, windowSize, attrs):
        """
        We don't support pseudo-terminal sessions.
        """

    def setEnv(self, name, value):
        """
        We don't support setting environment variables.
        """

    def execCommand(self, proto, cmd):
        """
        We don't support command execution sessions.
        """
        raise Exception("not executing commands")

    def openShell(self, transport):
        """
        Use our protocol as shell session.
        """
        protocol = EchoProtocol()
        # Connect the new protocol to the transport and the transport
        # to the new protocol so they can communicate in both directions.
        protocol.makeConnection(transport)
        transport.makeConnection(session.wrapProtocol(protocol))

    def eofReceived(self):
        pass

    def closed(self):
        pass


components.registerAdapter(
    ExampleSession, ExampleAvatar, session.ISession, session.ISessionSetEnv
)


class ExampleFactory(factory.SSHFactory):
    """
    This is the entry point of our SSH server implementation.

    The SSH transport layer is implemented by L{SSHTransport} and is the
    protocol of this factory.

    Here we configure the server's identity (host keys) and handlers for the
    SSH services:
    * L{connection.SSHConnection} handles requests for the channel multiplexing
      service.
    * L{userauth.SSHUserAuthServer} handlers requests for the user
      authentication service.
    """

    protocol = SSHServerTransport
    # Service handlers.
    services = {
        b"ssh-userauth": userauth.SSHUserAuthServer,
        b"ssh-connection": connection.SSHConnection,
    }

    def __init__(self):
        # Allow any username/password combination
        anyChecker = AcceptAnythingChecker()
        self.portal = portal.Portal(ExampleRealm(), [anyChecker])

    # Server's host keys.
    # To simplify the example this server is defined only with a host key of
    # type RSA.

    def getPublicKeys(self):
        """
        See: L{factory.SSHFactory}
        """
        return {b"ssh-rsa": keys.Key.fromFile(SERVER_RSA_PUBLIC)}

    def getPrivateKeys(self):
        """
        See: L{factory.SSHFactory}
        """
        return {b"ssh-rsa": keys.Key.fromFile(SERVER_RSA_PRIVATE)}

    def getPrimes(self):
        """
        See: L{factory.SSHFactory}
        """
        return PRIMES


if __name__ == "__main__":
    reactor.listenTCP(5022, ExampleFactory())
    reactor.run()
