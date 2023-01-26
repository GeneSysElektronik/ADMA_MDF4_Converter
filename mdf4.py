import re
import os
from threading import Thread
import time
from pandas import DataFrame
from asammdf import MDF
from progress.bar import IncrementalBar
from progress.spinner import Spinner
from bs4 import BeautifulSoup as bs

# ---------------------------------------------------------------------------- #
#                                    globals                                   #
# ---------------------------------------------------------------------------- #

version = "1.1.0"

xml_path = ""

"""Switch class
Used to deactivate a spinner in a seperate thread"""
class Switch:
    active = True

# ---------------------------------------------------------------------------- #
#                                   functions                                  #
# ---------------------------------------------------------------------------- #

"""Creates and runs a spinner in a seperate thread. Can be deactivated with the passed switch object"""
def wheel(switch):
    spinner = Spinner()
    while switch.active:
        spinner.next()
        time.sleep(0.5)

"""Processes gsda file. 
Reads a gsda file and saves it to a mdf4 file with channel groups
"""
def process_file(file):
    #Create a new Thread for a spinner and start it
    print("Opening file")
    s = Switch()
    t = Thread(target=wheel,args=[s])
    t.start()

    
    lines = file.readlines()

    #First line are channel names
    channels = lines[0].strip(", \n").split(",")
    #Rest of the lines are data in the same order as the channels
    data_lines = [line.strip(",\n").split(",") for line in lines[1:]]

    read_bar = IncrementalBar("Reading gsda", max = len(data_lines), suffix='%(percent)d%%')
    data = []

    #Stop the spinner and join the thread
    s.active = False
    t.join()

    for line in data_lines:
        data.append([float(val) for val in line])
        read_bar.next()

    print("\nGenerating Channelgroups...")

    s.active = True
    t = Thread(target=wheel,args=[s])
    t.start()

    #generate pandas DataFrame to improve performance and make it easier to divide data in channel groups
    adma_df = DataFrame(data=data,columns=channels)
    channel_groups = get_channel_groups(adma_df)
    mdf = MDF()
    
    s.active = False
    t.join()

    convert_bar = IncrementalBar("Converting", max = len(channel_groups.keys()), suffix='%(percent)d%%')

    for group in channel_groups.keys():
        #Get subset of dataframe with all channels belonging to the current channel groud
        sub = adma_df[channel_groups[group]]
        #Append the subset to the mdf object, automatically creates new channelgroup in the mdf
        mdf.append(sub)
        #Add the name of the group as a channel
        mdf.groups[-1].channel_group.comment = group
        convert_bar.next()

    print("\nSaving...")

    return mdf

"""Generates channel groups
Generates a dictionary with the keys being the channel group names retrieved from the xml file.
Values are lists of channel names.
Enables easy retrieval of channel names if given the channel group name
"""
def get_channel_groups(dataframe):
    channel_groups = {}
    #If none is entered as xml, returns all channels in one group named "none"
    if xml_path.lower() == "none":
        channel_groups["none"] = dataframe.columns
        return channel_groups

    else:
        #parse xml with bs4
        content = []
        with open(xml_path) as file:
            content = file.readlines()
        content = "".join(content)
        xml_content = bs(content, "lxml")

        #creates a dictionary with the individual channels as keys
        #values are package names
        #helps to associate a channel name with its group for generating the main dictionary later
        channel_package_dict = {}
        for package in xml_content.findAll("package"):
            for tag in package.findAll("channel"):
                channel_package_dict[tag.get("name")] = package.get("name")

        #Iterates over all channel names and tries to get the corresponding package name
        #If the channel is not in the package dictionary, it gets appended to the "none" group
        #The channel not being in the package dict can happen if, for example, the wrong version of xml was used
        for channel in dataframe.columns:
            channel_groups.setdefault(channel_package_dict.get(channel,"None"),[]).append(channel)
        
        return channel_groups

        

# ---------------------------------------------------------------------------- #
#                                   commands                                   #
# ---------------------------------------------------------------------------- #

"""Command class
Abstract class to define commands
name, command and description are for display in the help command only
name: Name of the command
command: Command that has to be entered in readable text
description: More detailed description if needed. Optional

regex: This regex needs to be matched for the command to be executed. Not case sensitive
"""
class Command:
    name = ""
    command = ""
    regex = ""
    description = ""

    #Tries to execute this command. Returns true if the regex was matched, false if not
    #If the command fails to execute, e.g. because of incorrect arguments, the exception message is printed
    def try_execute(self, input):
        if m := re.search(self.regex, input, re.IGNORECASE):
            try:
                self.execute(m.groups())
            except Exception as e:
                print(str(e))
            return True
        else:
            return False

    def execute(self,input):
        pass



class ReadDirectory(Command):
    name = "Convert all gsda files in a directory to mdf4"
    command = "gsda-mdf-dir [path]"
    regex = "^gsda-mdf-dir (.+)"

    def execute(self, args):
        if xml_path == "":
            raise Exception("No xml provided. Enter 'gsda-mdf-xml none' to not use an xml")

        dir = args[0]
        #replace forward slashes to keep file paths consistent
        dir = dir.replace("/","\\")
        dir = dir.strip("\"")
        if not os.path.isdir(dir):
            raise Exception("Couldn't find directory")
        
        save_path = dir + "\\converted"

        #retrieves all file names in the given directory that end with ".gsda"
        file_names = [f for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f)) and re.search(".*\.gsda",f)]

        for i,file_name in enumerate(file_names):
            with open(os.path.join(dir,file_name)) as file:
                print(f"{i+1}/{len(file_names)}")
                mdf = process_file(file)
                mdf.save(os.path.join(save_path,file_name))
        
        print("Done")

class ReadFile(Command):
    name ="Convert a single file from gsda to mdf4"
    command="gsda-mdf-file [path]"
    regex = "^gsda-mdf-file (.+)"

    def execute(self,args):
        if xml_path == "":
            raise Exception("No xml provided. Enter 'gsda-mdf-xml none' to not use an xml")

        dir = args[0]
        dir = dir.replace("/","\\")
        dir = dir.strip("\"")
        if not os.path.isfile(dir):
            raise Exception("File not found")

        if not re.search(".*\.gsda",dir):
            raise Exception("Invalid format")

        save_path = dir.replace(".gsda",".mf4")

        with open (dir) as file:
            mdf = process_file(file)
            mdf.save(save_path,overwrite=True)

        print("Done")

class Quit(Command):
    name = "Quit"
    command = "q"
    regex = "^q"

    def execute(self, args):
        print("Quitting")
        time.sleep(0.5)

class Help(Command):
    name = "Help"
    command = "h"
    regex = "^h"

    def execute(self, args):
        for c in commands:
            print(c.command + ": "+ c.name)
        print("\n")

class Xml(Command):
    name = "Select an xml file to generate channel groups when converting gsda to mf4. Enter 'none' to disable grouping."
    command = "gsda-mdf-xml [none/path]"
    regex = "^gsda-mdf-xml (.+)"

    def execute(self, args):
        dir = args[0]
        dir = dir.replace("/","\\")
        dir = dir.strip("\"")
        if dir.lower() != "none":
            if os.path.isfile(dir):
                if not re.search(".*\.xml", dir):
                    raise Exception("Invalid format")
            else:
                raise Exception("Invalid path")
        global xml_path
        xml_path = dir
        print("OK")

class FileToMat(Command):
    name = "Convert a single file from mdf4 to mat"
    command = "mdf-mat-file [path]"
    regex = "^mdf-mat-file (.+)"

    def execute(self, args):
        dir = args[0]
        dir = dir.replace("/","\\")
        dir = dir.strip("\"")
        if not os.path.isfile(dir):
            raise Exception("File not found")

        if not re.search(".*\.mf4",dir):
            raise Exception("Invalid format")

        save_path = dir.replace(".mf4",".mat")

        with open (dir) as file:
            mdf = MDF(dir)
            mdf.export("mat",save_path, overwrite=True)

        print("Done")

class DirToMat(Command):
    name = "Convert all mdf4 files in a directory to mat"
    command = "mdf-mat-dir [path]"
    regex = "^mdf-mat-dir (.+)"

    def execute(self,args):
        dir = args[0]
        dir = dir.replace("/","\\")
        dir = dir.strip("\"")
        if not os.path.isdir(dir):
            raise Exception("Directory not found")
        
        save_path = dir + "\\matlab"
        os.mkdir(save_path)

        file_names = [f for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f)) and re.search(".*\.mf4",f)]  

        bar = IncrementalBar("Converting", max = len(file_names), suffix='%(percent)d%%')
        for file_name in file_names:
            mdf = MDF(os.path.join(dir,file_name))
            mdf.export("mat",os.path.join(save_path,file_name))
            bar.next()
                
        
        print("Done")

#List of commands. The help command will display information in the same order as this list is in.
#Commands can be enabled/disabled by adding/removing them in this list
commands = [
    Xml(),
    ReadFile(),
    ReadDirectory(),
    FileToMat(),
    DirToMat(),
    Help(),
    Quit()
]

# ---------------------------------------------------------------------------- #
#                                    script                                    #
# ---------------------------------------------------------------------------- #

clear = lambda: os.system('cls')
clear()

print("\n\n\n")
print("\t                             ,,,,,    ")
print("\t                            ,,,,,,,,  ")
print("\t                            ,,,,,,,   ")
print("\t                        ,,,     ,     ")
print("\t                    ,,,         ,,    ")
print("\t                ,,,             ,,    ")
print("\t     ,,,,,, ,,,                 ,,    ")
print("\t   ,,,,,,,,,,                    ,    ")
print("\t   ,,,,,,,,,,,                   ,,   ")
print("\t   .,,,,,,,,,  ,,,,,,            ,,   ")
print("\t       ,,,              ,,,,,,   ,,,, ")
print("\t                                ,,,,,,")
print("\t                                 ,,,")
print("\n")
print("\t**********************************************")
print("\t**********  GeneSys MDF4 Converter  **********")
print("\t**********************************************")
print(f"\tVersion {version}")
print("\n\n\n")
print(f"Help: {Help.command}")

comm = ""

while comm != Quit.command:
    try:
        comm = input()
        if not any([c.try_execute(comm) for c in commands]):
            print("Command not recognized")
    except KeyboardInterrupt:
        print("Quitting")
        time.sleep(0.5)
        os._exit(status=0)

    
