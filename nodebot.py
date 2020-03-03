import codecs
import datetime
import json
import platform
import random
import re
import socket
import sys
import time

print("Running on " + platform.system())

non_bmp_map = dict.fromkeys(range(0x10000, sys.maxunicode + 1), 0xfffd)

settings = open("config.json")
settings = json.load(settings)


# --------------------------------------------- Start Settings -----------------------------------------------------
HOST = "irc.twitch.tv"                          # Hostname of the IRC-Server in this case twitch's
PORT = 6667                                     # Default IRC-Port
CHAN = settings["channel"]                      # Channelname = #{Nickname}
NICK = settings["username"]                     # Nickname = Twitch username
PASS = settings["oauth"]                        # www.twitchapps.com/tmi/ will help to retrieve the required authkey
# --------------------------------------------- End Settings -------------------------------------------------------

#command levels
USER = 10
MOD = 25
BROADCASTER = 50

# Open necessary files

try:
    open(CHAN[1:] + ".log")
except FileNotFoundError:
    f = open(CHAN[1:] + ".log", "w", encoding="utf-8")
    f.write("BEGIN OF LOG GENERATED ON " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + "\n")
    f.write("ALL TIMES ARE REPRESENTED IN UTC\n")
    f.flush()
    f.close()

logfile = open(CHAN[1:] + ".log", "a", encoding="utf-8")

try:
    open(CHAN[1:] + "_commands.json")
except FileNotFoundError:
    f = open(CHAN[1:] + "_commands.json", "w", encoding="utf-8")
    f.write("{}") # TODO: Write example code here
    f.flush()
    f.close()
    
command_file = open(CHAN[1:] + "_commands.json", "r+") # opening this file for read+write as that is what we will do

# --------------------------------------------- Start Functions ----------------------------------------------------
def send_pong(msg):
    con.send(bytes('PONG %s\r\n' % msg, 'UTF-8'))


def send_message(chan, msg):
    con.send(bytes('PRIVMSG %s :%s\r\n' % (chan, msg), 'UTF-8'))
    print(NICK + ": " + msg)


def send_nick(nick):
    con.send(bytes('NICK %s\r\n' % nick, 'UTF-8'))


def send_pass(password):
    con.send(bytes('PASS %s\r\n' % password, 'UTF-8'))


def join_channel(chan):
    con.send(bytes('JOIN %s\r\n' % chan, 'UTF-8'))


def part_channel(chan):
    con.send(bytes('PART %s\r\n' % chan, 'UTF-8'))

# -------------------------------------------------- Magic ---------------------------------------------------------

# Load the commands file, if no commands exist, fill it with a default list of commands
commands = json.load(command_file)
if not commands:
    commands = {
                    "!help":
                        {
                            "type": "text",
                            "return": "Add commands with !addcom, edit them with !editcom, and delete with !delcom"
                        },
                    "!addcom":
                        {
                            "type": "built-in"  # A built in command will override any options here
                                                # I just put this here to remember what functions are built in
                        },
                    "!editcom":
                        {
                            "type": "built-in"
                        },
                    "!delcom":
                        {
                            "type": "built-in"
                        },
                    "!h":
                        {
                            "type": "alias",
                            "return": "!help"
                        },
                    "!commands":
                        {
                            "type": "built-in"
                        }
                }
    update_commands_file()

# updates the commands file to reflect the current state of the commands. Sorts all commands alphabetically
def update_commands_file():
    command_file.seek(0)
    command_file.truncate() # remove all text in the command file, which is "{}" at this moment
    command_file.flush()
    json.dump(commands, command_file, indent=4, sort_keys=True)
    command_file.flush()

def text_command(command):
    # TODO: All magic that will allow this to work by finding {}s and output properly formatted output_text
    # Got file handling working
    # TODO: Find a more elegant solution to this
    finder = re.compile(r"(?<=\{)(.*?)(?=\})") # Regex command to find all variables within {}
    found = finder.finditer(commands[command]["return"])
    input_text = finder.split(commands[command]["return"])
    output_text = []
    for item in input_text: # especially with this shit
        if item[-1] == "{":
            item = item[:-1]
        if item[0] == "}":
            item = item[1:]
        output_text.append(item)
    print(output_text)
    for item in found:
        # print(item.group(0))
        flags = re.split(":", item.group(0))
        if flags[0] == "file":
            output = read_text_file(command, flags[1])
            for index, text in enumerate(output_text):
                if text == item.group(0):
                    output_text[index] = output
    
    text_out = ""
    for item in output_text:
        text_out = text_out + item
    send_message(CHAN, text_out)
    
# Returns a random line from the text file, unless command is indexed
# If command is indexed, and no index is provided, the index is returned
# while the line chosen is random. Otherwise the line at the index is returned
def read_text_file(command, file_to_read, count_lines=False):
    infile = open(file_to_read)
    lines = infile.readlines()
    if count_lines:
        return len(lines) - 1 # - 1 to ensure the maximum value is interpreted by end users correctly
    if commands[command]["indexed"]:
        index = getInteger(message[len(command) + 1:])
        if index >= 0 and index < len(lines) and not isinstance(index, bool):
            pass
        else:
            index = random.randrange(0, len(lines))
        output = str(index) + ": " + lines[index]
    else:
        output = random.choice(lines)
    return output


def text_file_command(command):
    # start by finding all regex expressions for math, files, etc
    # this regex commands finds all text between { and }
    # TODO: implement the rest of the message into the output, including random and math
    finder = re.compile(r"(?<=\{)(.*?)(?=\})")
    found = finder.findall(commands[command]["return"]) 
    for item in found: 
        if item[:5] == "file:":
            break
    input_file = open(infile)
    lines = input_file.readlines()
    if commands[command]["indexed"]:
        index = getInteger(message[len(command + " "):])
        print("INDEX: " + str(index))
        if index >= 0 and index < len(lines) and not isinstance(index, bool): # Python classifies bools as ints
            output = lines[index]                                             # but not ints as bools
            print(index)
        else:
            index = random.randrange(0,len(lines))
            output = lines[index]
    else:
        output = random.choice(lines)
    send_message(CHAN, output)

def do_command(command):
    if commands[command]["type"] == "alias": # jumps all the way down to final alias
        command = commands[command]["return"]
    if commands[command]["type"] == "text":
        text_command(command)
    elif commands[command]["type"] == "text-file":
        text_command(command)
                
    
        

# -------------------------------------------- Built in Functions --------------------------------------------------

def listcom():
    comstr = ""
    for com in commands:
        comstr += com + ", "
    comstr = comstr[:-len(", ")] # trim the end
    send_message(CHAN, comstr)

def addcom(edit=False):
    if user_command_level >= MOD:
        text = message[len("!addcom "):]
        command_name, command_type, command_output = re.split(";", text, maxsplit=2)
        command_name = command_name.strip()
        command_type = command_type.strip()
        command_output = command_output.strip()
        if command_name in commands and not edit:
            send_message(CHAN, "Cannot add command %s, exists" % (command_name))
        elif command_type == "alias" and commands[command_output]["type"] == "alias":
            send_message(CHAN, "Cannot add aliases of aliases")
        else:
            commands[command_name] = {"type": command_type, "return": command_output}
            update_commands_file()
            #print(repr(commands))
            if edit: send_message(CHAN, "Command %s successfully edited" % (command_name))
            else: send_message(CHAN, "Command %s successfully added" % (command_name))

def editcom():
    if user_command_level >= MOD:
        text = message[len("!editcom "):]
        text = "!addcom " + text    
        addcom(edit=True)

def delcom():
    if user_command_level >= MOD:
        text = message[len("!delcom "):]
        text = text.strip()
        if text not in commands:
            send_message(CHAN, "Cannot delete nonexistent command")
        else:
            del commands[text]
            update_commands_file()
            send_message(CHAN, "Command %s successfully deleted" % (text))

# --------------------------------------------- Helper Functions ---------------------------------------------------

def get_sender(msg):
    result = ""
    for char in msg:
        if char == "!":
            break
        if char != ":":
            result += char
    return result

def get_message(msg):
    result = ""
    i = 3
    length = len(msg)
    while i < length:
        result += msg[i] + " "
        i += 1
    #print(user_command_level)
    result = result[1:]
    return result

options = {}

def parse_message(msg):
    global options
    if len(msg) >= 1:
        msg = msg.split(' ')
        options =  {"!addcom": addcom,
                    "!editcom": editcom,
                    "!delcom": delcom,
                    "!commands": listcom}
        
        #update !commands with new commands only
        for key in options:
            if key not in commands:
                commands[key] = {"type": "built-in"}
                update_commands_file()

        if msg[0] in options:
            options[msg[0]]()
        elif msg[0] in commands:
            do_command(msg[0])
    

def getInteger(s):
    try:
        int(s)
        return int(s)
    except ValueError:
        return False
    

# -------------------------------------------------------------------------------
con = socket.socket()
con.connect((HOST, PORT))

def connect():
    send_pass(PASS)
    send_nick(NICK)
    join_channel(CHAN)
    con.send(bytes('CAP REQ :twitch.tv/tags\r\n', 'UTF-8'))
    con.send(bytes('CAP REQ :twitch.tv/commands\r\n', 'UTF-8'))
    con.send(bytes('CAP REQ :twitch.tv/membership\r\n', 'UTF-8'))

connect()

data = ""

while True:
    try:
        data = data+con.recv(1024).decode("UTF-8", errors="ignore")
        if len(data) == 0:
            connect()

        data_split = re.split(r"[~\r\n]+", data)
        #print(data_split)
        data = data_split.pop()

        if data_split[0][:4] != "PING":
            data_split = re.split(":", data_split[0], 1)
        data_split_dict = {}
        data_split_list = re.split(";", data_split[0])
        
        #create tags, filling blank ones with empty strings
        for item in data_split_list:
            item = re.split("=", item, 1)
            
            #set message, workaround.
            if item[0] == "user-type":
                data_split_dict["user-type"] = data_split[-1]
            else:
                try:
                    data_split_dict[item[0]] = item[1]
                except IndexError:
                    data_split_dict[item[0]] = ""

        #print(data_split_dict)
        #default user level
        user_command_level = 10
        if "user-type" in data_split_dict:
            if data_split_dict["mod"] == "1":
                user_command_level = 25
                #if a mod is detected, remove the mod from user-type, this ensures that get_message will still work
                #TODO: make this more robust
                if data_split_dict["user-type"][3:] == "mod":
                    data_split_dict["user-type"] = data_split_dict["user-type"][3:]
            
            for line in [data_split_dict["user-type"]]:
                line = str.rstrip(line)
                line = str.split(line)

                if line[1] == "PRIVMSG":
                    sender = get_sender(line[0])
                    #if "bits" in data_split_dict:
                    #    add_bits(sender, data_split_dict["bits"])
                    #broadcaster will always be the channel name, has complete authority over bot
                    if sender == CHAN[1:]:
                        user_command_level = 50
                    message = get_message(line)
                    parse_message(message)
                    
                    print("[" + str(user_command_level) + "] " + sender + ": " + message.translate(non_bmp_map))
                    logfile.write(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + " [" + str(user_command_level) + "] " + sender + ": " + message + "\n")
                    logfile.flush()

        else:
            for line in data_split:
                line = str.rstrip(line)
                line = str.split(line)
                if len(line) >= 1:
                    if line[0] == "PING":
                        send_pong(line[1])
                        print("sending pong")


    except socket.error:
        print("Socket died")

    except socket.timeout:
        print("Socket timeout")
