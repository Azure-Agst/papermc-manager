#!/usr/bin/env python3

#
# PaperMC Server Manager
# (c) 2021 azure_agst
#

import os
import sys
import time
import glob
import libtmux
import logging
import argparse
import requests
import configparser
from datetime import datetime

# static declarations
CONFIG_FILE = "./manager_config.ini"

# global variables
config = None
server = None

# main function declaration
def main():

    # global declarations
    global config, server

    # initialize logging
    logging.basicConfig(
        filename='manager.log', level=logging.INFO,
        format='%(asctime)s:%(levelname)s:%(message)s'
    )
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    # print initial statement
    logging.info(f"Manager started with args: {sys.argv}")

    # initialize argument parser
    parser = argparse.ArgumentParser(description='Manage Minecraft server using Python and Tmux.')
    parser.add_argument('action', choices=['start', 'stop', 'restartmacro'], help='Required Action Argument')

    # check number of arguments
    if len(sys.argv) != 2:
        logging.error("Invalid number of arguments specified!")
        parser.print_help()
        return -1
    args = parser.parse_args()

    # initialize config
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        logging.error("Config file missing! Please create a config file.")
        return -1
    config.read(CONFIG_FILE)

    # initialize tmux api
    server = libtmux.Server()

    # main switch depending on argument
    if args.action == "start":
        return start_server()
    elif args.action == "stop":
        return stop_server()
    elif args.action == "restartmacro":
        return restart_macro()
    else:
        logging.critical("Reached block that should never be met? Shutting down...")
        return -1


# start server declaration
def start_server():

    # global declarations
    global config, server

    # static declarations
    session = config['manager']['session_name']
    version = config['manager']['target_version']

    # print that we're starting server
    logging.info(f"Attempting to start server...")

    # try to update
    update_paper()

    # determine latest server
    server_jar_list = glob.glob(f"paper-{version}-*.jar")
    server_jar_list.sort(reverse=True)
    if len(server_jar_list) < 1:
        logging.error(f"No server jar found! Exiting...")
        return -1
    latest_jar = server_jar_list[0]

    # try to list sessions and make if not running
    # if this fails, it means tmux is not running
    try:
        cur_sessions = server.find_where({ "session_name": session })
        logging.info("Tmux server is currently running! Checking if server is live...")

        if cur_sessions is not None:
            logging.error(f"Session '{session}' is already running! Exiting...")
            return -1

        else:
            logging.info(f"Session '{session}' is not live! Starting using api...")
            server.new_session(session_name=session, attach=False)

    except libtmux.exc.LibTmuxException:
        logging.info("Tmux server is not live, starting session via cmd...")
        os.system(f"tmux new-session -d -s {session}")
        
    # sleep a second to give server time to come up
    time.sleep(1)

    # get running session
    t = server.find_where({ "session_name": session }).attached_window.attached_pane

    # by this point 't' should be a tmux session object
    # tell tmux to start the server
    logging.info(f"Connected to session, Starting server...")
    t.send_keys(f"/usr/bin/env java {config['manager']['server_args']} -jar {latest_jar} nogui", enter=True)

    # log that we're done :)
    logging.info(f"Server created within Tmux session '{session}'!")

    # return
    return 0

# stop server declaration
def stop_server():

    # global declarations
    global config, server

    # static declarations
    session = config['manager']['session_name']

    # print that we're stopping server
    logging.info(f"Attempting to stop server...")

    # see if our session is running
    # if this fails, it means tmux is not running
    try:
        cur_sessions = server.find_where({ "session_name": session })
        if cur_sessions is None:
            logging.error(f"Session '{session}' is not running! Exiting...")
            return -1

    except libtmux.exc.LibTmuxException:
        logging.error("Tmux server is not live, exiting...")
        return -1

    # get running session
    t = server.find_where({ "session_name": session }).attached_window.attached_pane

    # we can assume that we're within the server command line at this point
    logging.info(f"Connected to session, Stopping server...")
    t.send_keys('tellraw @a {"text":"The server is shutting down!","color":"red"}', enter=True)
    t.send_keys('stop', enter=True)

    # sleep 5 to give server time to come down
    time.sleep(5)

    # log that we're done :)
    logging.info(f"Server has been shut down! Killing tmux session...")

    # kill tmux session
    server.kill_session(target_session=session)

    # print and return
    logging.info(f"Session has been killed! All done!")
    return 0

# restart server macro
def restart_macro():

    # global declarations
    global config, server

    # static declarations
    session = config['manager']['session_name']

    # print that we're stopping server
    print("Be warned, ye who calls this from bash! It takes 15 minutes and is meant to be scheduled!")
    logging.info(f"Starting server restart macro...")

    # see if our session is running
    # if this fails, it means tmux is not running
    try:
        cur_sessions = server.find_where({ "session_name": session })
        if cur_sessions is None:
            logging.error(f"Session '{session}' is not running! Exiting...")
            return -1

    except libtmux.exc.LibTmuxException:
        logging.error("Tmux server is not live, exiting...")
        return -1

    # get running session
    t = server.find_where({ "session_name": session }).attached_window.attached_pane

    # we can assume that we're within the server command line at this point
    logging.info(f"Connected to session...")

    # define increments for macro
    incs = [
        ("10 minutes", 300), ("5 minutes", 120), ("3 minutes", 60), ("2 minutes", 60), ("1 minute", 30), ("30 seconds", 15),
        ("15 seconds", 10), ("5 seconds", 1), ("4 seconds", 1), ("3 seconds", 1), ("2 seconds", 1), ("1 seconds", 1), 
    ]

    # execute macro
    for slice in incs:
        logging.info(f"{slice[0]} to restart...")
        t.send_keys('tellraw @a {"text":"The server is restarting in '+slice[0]+'!","color":"red"}', enter=True)
        time.sleep(slice[1])

    # bring down server
    stop_server()

    # bring server back up
    start_server()

    # we should be done here!
    return 0

# update paper jar function
def update_paper():

    # global declarations
    global config, server

    # static declarations
    version = config['manager']['target_version']

    # print statement
    logging.info("Update_paper() called, attempting to update server jar...")

    # this link is not a redirect, it returns latest jar directly
    # the jar file name is in hidden in the content-disposition header
    # paper uses the filename*=UTF-8'' prefix so we remove that to get name
    download_url = f"https://papermc.io/api/v1/paper/{version}/latest/download"

    # download latest jar
    with requests.get(download_url, stream=True) as stream:

        # get filename from headers
        file = stream.headers['content-disposition'].replace("attachment; filename*=UTF-8''", "")

        # if that file already exists, close connection and return
        if os.path.exists(file):
            logging.info("No need to update, already have latest version!")
            stream.close()
            return -1

        # write everything to file
        logging.info(f"Downloading new paper version {file}...")
        with open(file, 'wb') as outfile:
            for chunk in stream.iter_content(chunk_size=8192):
                outfile.write(chunk)

    # remove old paper versions
    jar_list = glob.glob(f"paper-{version}-*.jar")
    jar_list.remove(file)  # exclude latest version
    for old_jar in jar_list:
        os.remove(old_jar)
        logging.info(f"Removed old version: {old_jar}")
    
    # return
    return 0

# make sure this is started directly
if __name__ == "__main__":
    exit(main())