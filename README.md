# PaperMC Manager

A project I made to help manage PaperMC servers hosted on MacOS 10.15 Catalina.

*This project will not be actively maintained.*

## 1.) How it Works

This project consists of two parts: a primary python script, and the plists needed to tell launchd to load them at boot.

The python script takes one argument, which must be one of the following: `start`, `stop`, or `restartmacro`

- `start` starts the server in within tmux session with the name specified in `manager_config.ini`
- `stop` gracefully stops the server within its tmux session, then kills the tmux session.
- `restartmacro` should only be called by launchd, as it is meant to run on a schedule. It handles warning the users that a restart is pending, then gracefully updates and restarts the server.

The second part of the project consists of the plists used to load/schedule items with launchd.

- `local.mc.server` is the service that handles starting the server up within tmux after cold boot/reboot.
- `local.mc.restarter` is the service that runs nightly and restarts/updates the server

## 2.) How to Install

1.) Copy `manager.py`, `requirements.txt`, and `manager_config.ini` to your minecraft server's folder, then run the following within it:

```bash
$ pip3 install -r requirements.txt
```

2.) Modify the two plist files in `plist/` to your liking.
- Be sure to update all paths, usernames, and desired restart times
- Restart time should have 10 minutes subtracted from the desired restart time, as that's how long the macro takes to run.
- A good reference website for syntax is [Launchd.Info][launchd-info].

3.) Copy those two files into `/Library/LaunchDaemons` and tell launchd to load them as follows:

```bash
$ sudo launchctl load -w /Library/LaunchDaemons/local.mc.server.plist
$ sudo launchctl load -w /Library/LaunchDaemons/local.mc.restarter.plist
```

4.) Check to make sure that they have been loaded properly using launchctl:

```bash
$ sudo launchctl list | grep local.mc
-       0       local.mc.restarter
-       0       local.mc.server
```

5.) Restart the machine! Afterwards, when you log in to whichever user you specified in the plists, you should see an active tmux session that contains your server.

|**Note**|
|:-:|
|Obviously, some of these commands may not work as expected on the first run. Your machine's environment is almost surely different than mine, and you may have to edit some paths to executables or whatnot to get everything to work. Such is the way of being a sysadmin, I presume. I believe I've commented everything well enough that you can tear it apart if you need to. :)|

## 3.) Troubleshooting

### Server not starting properly?

Check the logs in `manager.log` and see what it says. If that doesn't help, try launching `manager.py` directly and seeing if it fails.

### Manager works when I run it directly, but not when launchd does!

Launchd is a PITA to debug, so I can't really give you any solid suggestions here.

I would suggest running `sudo launchctl list | grep local.mc` and seeing if the second number before the service you're debugging is zero. That's the service's last exit code. If positive and nonzero, `launchctl error [number]` might give you a lead as to what went wrong.

Other than that, Google is your friend.

### Launchctl list shows manager returned 0, but the server still isn't started?

Check `manager.log` and see if it contains any errors.

If none, connect to the tmux session using `tmux a` while logged into the user who owns the server process, and seeing what it says.

I had a weird case once where java was Killed by the kernel after a reboot for seemingly no reason. Running `sudo dmesg | grep -E -i -B100 'java'` revealed the following:

```
Security policy would not allow process: 314, /Library/Java/JavaVirtualMachines/jdk-16.0.1.jdk/Contents/Home/bin/java
```

It turns out that for some reason, my computer's security policies prevented my openjdk install from running, despite it being able to run on the machine before then. Resolving this required me to hook up a monitor to the machine, log into the server as the server-hosting user, and accept the popup asking if I wanted to allow java to run. Since then I haven't had the issue reappear, so I assume it's a one-and-done.

### Why are you hosting a server on a Mac of all things? Why not a better Linux or Windows VM?

Don't ask.

## 4.) Config reference

```ini
[manager]
; target server version
target_version=1.17.1
; desired tmux session name
session_name=paper
; args to launch server with. i suggest using aikar's flags :)
; https://blog.airplane.gg/aikar-flags/
server_args=-Xms4G -Xmx4G
```

[launchd-info]: https://www.launchd.info/